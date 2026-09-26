from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    hash_password,
    validate_password_strength,
)
from app.models.audit_log import AuditAction, AuditLog
from app.models.candidate_profile import CandidateProfile, CandidateProfileStatus
from app.models.organization import Organization, OrganizationType, OrganizationVerificationStatus
from app.models.institution_profile import InstitutionProfile, InstitutionVerificationStatus
from app.models.role import Role
from app.models.signup_session import SignupVerificationSession
from app.models.user import User
from app.models.user_role import UserRole
from app.models.verification_challenge import VerificationChallenge
from app.models.verification_application import VerificationApplication, VerificationStatus
from app.models.notification import NotificationPriority, NotificationType
from app.core.events import event_manager
from app.services.notification_service import NotificationService
from app.services.jurisdiction_service import (
    get_eligible_verifier_user_ids,
    resolve_government_unit_for_registration,
)
from app.services.username_service import generate_available_username, is_username_available, normalize_username
from app.services.auth_service import (
    _default_role_for_account_type,
    _get_phone_variations,
    _normalize_identifier,
    create_auth_session,
)
from app.services.otp_delivery_service import (
    DeliveryError,
    _is_testing_environment,
    deliver_otp,
)

OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 10
MAX_OTP_ATTEMPTS = 5


class VerificationError(Exception):
    """Base verification error."""


class InvalidChannelError(VerificationError):
    """Email or phone is missing or invalid."""


class AlreadyVerifiedError(VerificationError):
    """The requested contact method is already verified."""


class InvalidOTPError(VerificationError):
    """The supplied OTP is invalid."""


class OTPExpiredError(VerificationError):
    """The OTP has expired."""


class OTPAttemptsExceededError(VerificationError):
    """Too many incorrect OTP attempts."""


class OTPAlreadyUsedError(VerificationError):
    """The OTP has already been consumed."""


class ResendCooldownError(VerificationError):
    """Raised when OTP resend is attempted before the cooldown window expires."""


class MaxResendsExceededError(VerificationError):
    """Raised when maximum OTP resends have been exceeded for a session."""


def generate_otp() -> str:
    """Generate a cryptographically secure six-digit OTP."""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(otp: str) -> str:
    """Hash OTP using SHA-256 before storing it in the database."""
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_contact_value(user: User, channel: str) -> str:
    channel = channel.upper()

    if channel == "EMAIL":
        if not user.email:
            raise InvalidChannelError("No email address is registered.")
        return user.email

    if channel == "PHONE":
        if not user.phone:
            raise InvalidChannelError("No phone number is registered.")
        return user.phone

    raise InvalidChannelError("Channel must be EMAIL or PHONE.")


def _is_already_verified(user: User, channel: str) -> bool:
    channel = channel.upper()

    if channel == "EMAIL":
        return user.email_verified

    if channel == "PHONE":
        return user.phone_verified

    return False


async def request_otp(
    db: AsyncSession,
    user: User,
    channel: str,
    purpose: str = "SIGNUP",
) -> tuple[VerificationChallenge, str]:
    """
    Create a new OTP challenge and dispatch it through real email/SMS provider.
    Raw OTP is NEVER logged or exposed.
    """
    channel = channel.upper()
    purpose = purpose.upper()

    contact = _get_contact_value(user, channel)

    if _is_already_verified(user, channel):
        raise AlreadyVerifiedError(
            f"{channel.lower().capitalize()} is already verified."
        )

    now = _now()

    # Rate limiting: Enforce resend cooldown window
    if not _is_testing_environment():
        res_recent = await db.execute(
            select(VerificationChallenge)
            .where(
                VerificationChallenge.user_id == user.id,
                VerificationChallenge.channel == channel,
                VerificationChallenge.purpose == purpose,
            )
            .order_by(VerificationChallenge.created_at.desc())
            .limit(1)
        )
        recent_challenge = res_recent.scalar_one_or_none()
        if recent_challenge and recent_challenge.created_at:
            cooldown = getattr(settings, "OTP_RESEND_COOLDOWN_SECONDS", 60)
            elapsed = (now - recent_challenge.created_at).total_seconds()
            if elapsed < cooldown:
                remaining = int(cooldown - elapsed)
                raise ResendCooldownError(
                    f"Please wait {remaining} seconds before requesting a new verification code."
                )

    # Invalidate previous unused challenges for the same user/channel/purpose.
    await db.execute(
        update(VerificationChallenge)
        .where(
            VerificationChallenge.user_id == user.id,
            VerificationChallenge.channel == channel,
            VerificationChallenge.purpose == purpose,
            VerificationChallenge.consumed.is_(False),
        )
        .values(consumed=True, consumed_at=now)
    )

    otp = generate_otp()

    challenge = VerificationChallenge(
        user_id=user.id,
        channel=channel,
        purpose=purpose,
        code_hash=hash_otp(otp),
        expires_at=now + timedelta(minutes=OTP_EXPIRY_MINUTES),
        attempts=0,
        max_attempts=MAX_OTP_ATTEMPTS,
        consumed=False,
    )

    db.add(challenge)
    await db.commit()
    await db.refresh(challenge)

    # Deliver via configured provider (SMTP for Email, Sandbox/MSG91 for SMS)
    await deliver_otp(channel, contact, otp)

    return challenge, otp


async def verify_otp(
    db: AsyncSession,
    user: User,
    channel: str,
    otp: str,
    purpose: str = "SIGNUP",
) -> User:
    """
    Verify the active OTP challenge for a user with constant-time SHA-256 hash comparison.
    """
    channel = channel.upper()
    purpose = purpose.upper()

    _get_contact_value(user, channel)

    result = await db.execute(
        select(VerificationChallenge)
        .where(
            VerificationChallenge.user_id == user.id,
            VerificationChallenge.channel == channel,
            VerificationChallenge.purpose == purpose,
            VerificationChallenge.consumed.is_(False),
        )
        .order_by(VerificationChallenge.created_at.desc())
        .limit(1)
    )

    challenge = result.scalar_one_or_none()

    if challenge is None:
        raise InvalidOTPError("No active verification code found.")

    now = _now()

    if challenge.consumed:
        raise OTPAlreadyUsedError("This verification code has already been used.")

    if now >= challenge.expires_at:
        raise OTPExpiredError("This verification code has expired.")

    if challenge.attempts >= challenge.max_attempts:
        raise OTPAttemptsExceededError(
            "Too many incorrect attempts. Please request a new code."
        )

    normalized_otp = str(otp).strip()

    if (
        len(normalized_otp) != OTP_LENGTH
        or not normalized_otp.isdigit()
        or not secrets.compare_digest(
            hash_otp(normalized_otp),
            challenge.code_hash,
        )
    ):
        challenge.attempts += 1
        await db.commit()

        if challenge.attempts >= challenge.max_attempts:
            raise OTPAttemptsExceededError(
                "Too many incorrect attempts. Please request a new code."
            )

        raise InvalidOTPError(
            f"Invalid verification code. "
            f"{challenge.max_attempts - challenge.attempts} attempts remaining."
        )

    challenge.consumed = True
    challenge.consumed_at = now

    if channel == "EMAIL":
        user.email_verified = True
    elif channel == "PHONE":
        user.phone_verified = True

    await db.commit()
    await db.refresh(user)

    return user


# =========================================================================
# Sequential Dual-Contact Signup Verification Flow
# =========================================================================

async def initiate_signup_session(
    db: AsyncSession,
    account_type: str,
    channel: str,
    identifier: str,
) -> tuple[SignupVerificationSession, str]:
    """
    Step 1: Choose Account Type & enter Mobile OR Email.
    Generates a secure random OTP and sends it through real provider.
    No user is created in PostgreSQL users table yet.
    """
    channel = channel.upper().strip()
    if channel not in ("EMAIL", "PHONE"):
        raise InvalidChannelError("Verification channel must be EMAIL or PHONE.")

    account_type = account_type.upper().strip()
    valid_types = {"CANDIDATE", "EMPLOYER", "TRAINING_INSTITUTE", "GOVERNMENT"}
    if account_type not in valid_types:
        raise VerificationError(f"Invalid account type '{account_type}'.")

    if channel == "EMAIL":
        norm_identifier = identifier.lower().strip()
        if "@" not in norm_identifier or len(norm_identifier) < 5:
            raise VerificationError("Invalid email address format.")

        # Check uniqueness in users
        res = await db.execute(select(User).where(User.email == norm_identifier))
        existing_users = res.scalars().all()
        if any(u.email_verified for u in existing_users):
            raise AlreadyVerifiedError("Email already registered")
    else:
        norm_identifier = _normalize_identifier(identifier)
        variations = _get_phone_variations(norm_identifier)
        res = await db.execute(select(User).where(User.phone.in_(variations)))
        existing_users = res.scalars().all()
        if any(u.phone_verified for u in existing_users):
            raise AlreadyVerifiedError("Phone already registered")

    now = _now()

    # Rate limiting: Enforce resend cooldown for the same contact in production
    cooldown = getattr(settings, "OTP_RESEND_COOLDOWN_SECONDS", 60)
    if not _is_testing_environment() and cooldown > 0 and settings.ENVIRONMENT == "production":
        res_recent_session = await db.execute(
            select(SignupVerificationSession)
            .where(
                SignupVerificationSession.primary_identifier == norm_identifier,
                SignupVerificationSession.completed.is_(False),
            )
            .order_by(SignupVerificationSession.created_at.desc())
            .limit(1)
        )
        recent_s = res_recent_session.scalar_one_or_none()
        if recent_s and recent_s.created_at:
            elapsed = (now - recent_s.created_at).total_seconds()
            if elapsed < cooldown:
                remaining = int(cooldown - elapsed)
                raise ResendCooldownError(
                    f"Please wait {remaining} seconds before requesting a new verification code."
                )

    otp = generate_otp()
    session_token = secrets.token_urlsafe(32)

    session = SignupVerificationSession(
        session_token=session_token,
        account_type=account_type,
        primary_channel=channel,
        primary_identifier=norm_identifier,
        primary_code_hash=hash_otp(otp),
        primary_verified=False,
        expires_at=now + timedelta(minutes=OTP_EXPIRY_MINUTES),
        attempts=0,
        max_attempts=MAX_OTP_ATTEMPTS,
        completed=False,
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Dispatch real OTP via SMTP or SMS
    try:
        await deliver_otp(channel, norm_identifier, otp)
    except DeliveryError as exc:
        from app.services.otp_delivery_service import logger
        logger.error("OTP delivery failed during signup verification: %s", exc)
        if not (settings.DEBUG or getattr(settings, "ALLOW_DEMO_EMAIL", False) or getattr(settings, "ALLOW_DEMO_SMS", False)):
            await db.delete(session)
            await db.commit()
            raise

    return session, session_token, otp


async def verify_primary_signup_otp(
    db: AsyncSession,
    session_token: str,
    otp: str,
) -> SignupVerificationSession:
    """
    Step 2: Verify primary contact OTP.
    """
    res = await db.execute(
        select(SignupVerificationSession).where(
            SignupVerificationSession.session_token == session_token,
            SignupVerificationSession.completed.is_(False),
        )
    )
    session = res.scalar_one_or_none()
    if not session:
        raise InvalidOTPError("Invalid or expired verification session.")

    now = _now()
    if now >= session.expires_at:
        raise OTPExpiredError("Verification code has expired. Please request a new code.")

    if session.attempts >= session.max_attempts:
        raise OTPAttemptsExceededError("Too many incorrect attempts. Please restart verification.")

    normalized_otp = str(otp).strip()
    if (
        len(normalized_otp) != OTP_LENGTH
        or not normalized_otp.isdigit()
        or not secrets.compare_digest(hash_otp(normalized_otp), session.primary_code_hash)
    ):
        session.attempts += 1
        await db.commit()
        if session.attempts >= session.max_attempts:
            raise OTPAttemptsExceededError("Too many incorrect attempts. Please restart verification.")
        raise InvalidOTPError(
            f"Invalid verification code. {session.max_attempts - session.attempts} attempts remaining."
        )

    session.primary_verified = True
    session.primary_verified_at = now
    session.attempts = 0
    await db.commit()
    await db.refresh(session)
    return session


async def initiate_secondary_signup_otp(
    db: AsyncSession,
    session_token: str,
    channel: str,
    identifier: str,
) -> SignupVerificationSession:
    """
    Step 3: Enter the other contact and send real OTP.
    """
    res = await db.execute(
        select(SignupVerificationSession).where(
            SignupVerificationSession.session_token == session_token,
            SignupVerificationSession.completed.is_(False),
        )
    )
    session = res.scalar_one_or_none()
    if not session:
        raise InvalidOTPError("Invalid or expired verification session.")

    if not session.primary_verified:
        raise VerificationError("Primary contact must be verified first.")

    channel = channel.upper().strip()
    if channel == session.primary_channel:
        raise VerificationError(
            f"Secondary contact must be the alternate method ({'PHONE' if session.primary_channel == 'EMAIL' else 'EMAIL'})."
        )

    if channel == "EMAIL":
        norm_identifier = identifier.lower().strip()
        if "@" not in norm_identifier:
            raise VerificationError("Invalid email address format.")
        # Check uniqueness
        res_e = await db.execute(select(User).where(User.email == norm_identifier))
        existing_e_users = res_e.scalars().all()
        if any(u.email_verified for u in existing_e_users):
            raise AlreadyVerifiedError("Email already registered")
    else:
        norm_identifier = _normalize_identifier(identifier)
        variations = _get_phone_variations(norm_identifier)
        res_p = await db.execute(select(User).where(User.phone.in_(variations)))
        existing_p_users = res_p.scalars().all()
        if any(u.phone_verified for u in existing_p_users):
            raise AlreadyVerifiedError("Phone already registered")

    now = _now()

    # Rate limiting: Enforce cooldown if secondary OTP was already dispatched in production
    if session.secondary_code_hash and not _is_testing_environment() and settings.ENVIRONMENT == "production":
        cooldown = getattr(settings, "OTP_RESEND_COOLDOWN_SECONDS", 60)
        last_sent = session.expires_at - timedelta(minutes=OTP_EXPIRY_MINUTES)
        elapsed = (now - last_sent).total_seconds()
        if elapsed < cooldown:
            remaining = int(cooldown - elapsed)
            raise ResendCooldownError(
                f"Please wait {remaining} seconds before requesting a new verification code."
            )

    otp = generate_otp()

    session.secondary_channel = channel
    session.secondary_identifier = norm_identifier
    session.secondary_code_hash = hash_otp(otp)
    session.secondary_verified = False
    session.expires_at = now + timedelta(minutes=OTP_EXPIRY_MINUTES)
    session.attempts = 0

    await db.commit()
    await db.refresh(session)

    # Dispatch real OTP via SMTP or SMS
    try:
        await deliver_otp(channel, norm_identifier, otp)
    except DeliveryError as exc:
        from app.services.otp_delivery_service import logger
        logger.error("Secondary OTP delivery failed: %s", exc)
        if not (settings.DEBUG or getattr(settings, "ALLOW_DEMO_EMAIL", False) or getattr(settings, "ALLOW_DEMO_SMS", False)):
            session.secondary_code_hash = None
            await db.commit()
            raise

    return session, otp


async def verify_secondary_signup_otp(
    db: AsyncSession,
    session_token: str,
    otp: str,
) -> SignupVerificationSession:
    """
    Step 4: Verify secondary contact OTP.
    """
    res = await db.execute(
        select(SignupVerificationSession).where(
            SignupVerificationSession.session_token == session_token,
            SignupVerificationSession.completed.is_(False),
        )
    )
    session = res.scalar_one_or_none()
    if not session:
        raise InvalidOTPError("Invalid or expired verification session.")

    if not session.primary_verified:
        raise VerificationError("Primary contact must be verified first.")

    if not session.secondary_code_hash:
        raise VerificationError("Secondary contact OTP has not been requested.")

    now = _now()
    if now >= session.expires_at:
        raise OTPExpiredError("Verification code has expired. Please request a new code.")

    if session.attempts >= session.max_attempts:
        raise OTPAttemptsExceededError("Too many incorrect attempts. Please request a new code.")

    normalized_otp = str(otp).strip()
    if (
        len(normalized_otp) != OTP_LENGTH
        or not normalized_otp.isdigit()
        or not secrets.compare_digest(hash_otp(normalized_otp), session.secondary_code_hash)
    ):
        session.attempts += 1
        await db.commit()
        if session.attempts >= session.max_attempts:
            raise OTPAttemptsExceededError("Too many incorrect attempts. Please request a new code.")
        raise InvalidOTPError(
            f"Invalid verification code. {session.max_attempts - session.attempts} attempts remaining."
        )

    session.secondary_verified = True
    session.secondary_verified_at = now
    session.attempts = 0
    await db.commit()
    await db.refresh(session)
    return session


async def complete_verified_signup(
    db: AsyncSession,
    session_token: str,
    password: str,
    terms_accepted: bool,
    additional_data: dict[str, Any],
) -> tuple[User, str, str, list[str]]:
    """
    Step 5: Final Account Creation.
    Ensures:
      - Sequential dual verification completed (both primary and secondary verified).
      - Terms and Privacy accepted.
      - Strong password validation.
      - Provisions active User with email_verified=True and phone_verified=True.
      - Provisions role profile in PostgreSQL.
      - Emits audit log.
      - Issues JWT access + refresh tokens.
    """
    if not terms_accepted:
        raise VerificationError("Terms of Service and Privacy Policy must be accepted to create an account.")

    res = await db.execute(
        select(SignupVerificationSession).where(
            SignupVerificationSession.session_token == session_token,
            SignupVerificationSession.completed.is_(False),
        )
    )
    session = res.scalar_one_or_none()
    if not session:
        raise InvalidOTPError("Invalid or expired verification session.")

    if not session.primary_verified or not session.secondary_verified:
        raise VerificationError("Both mobile number and email address must be verified before account creation.")

    validate_password_strength(password)

    # Determine email and phone from primary/secondary channels
    email = None
    phone = None
    if session.primary_channel == "EMAIL":
        email = session.primary_identifier
        phone = session.secondary_identifier
    else:
        phone = session.primary_identifier
        email = session.secondary_identifier

    # Double-check uniqueness in users (defense-in-depth)
    if email:
        res_e = await db.execute(select(User).where(User.email == email))
        if res_e.scalars().first():
            raise AlreadyVerifiedError("Email already registered")
    if phone:
        variations = _get_phone_variations(phone)
        res_p = await db.execute(select(User).where(User.phone.in_(variations)))
        if res_p.scalars().first():
            raise AlreadyVerifiedError("Phone already registered")

    account_type_str = session.account_type.upper()

    raw_username = additional_data.get("username")
    if raw_username:
        is_avail, avail_msg = await is_username_available(db, raw_username)
        if not is_avail:
            raise VerificationError(avail_msg)
        final_username = normalize_username(raw_username)
    else:
        seed = email.split("@")[0] if email else (phone or "user")
        final_username = await generate_available_username(db, seed)

    # Create the verified user
    user = User(
        email=email,
        phone=phone,
        username=final_username,
        password_hash=hash_password(password),
        account_type=account_type_str,
        email_verified=True,
        phone_verified=True,
        is_active=True,
        is_suspended=False,
    )
    db.add(user)
    await db.flush()

    # Assign default role
    role_code = _default_role_for_account_type(account_type_str)
    role_res = await db.execute(select(Role).where(Role.code == role_code))
    role = role_res.scalar_one_or_none()
    if role:
        db.add(UserRole(user_id=user.id, role_id=role.id))

    # Provision profile according to account type
    full_name = (
        additional_data.get("fullName")
        or additional_data.get("full_name")
        or (email.split("@")[0] if email else "User")
    )
    name_parts = full_name.strip().split(" ", 1)
    first_name = name_parts[0].capitalize()
    last_name = name_parts[1].capitalize() if len(name_parts) > 1 else ""

    # Resolve jurisdiction government unit based on location and level
    target_state = (
        additional_data.get("state")
        or additional_data.get("candidateState")
        or additional_data.get("instState")
        or additional_data.get("govtState")
    )
    target_city = (
        additional_data.get("city")
        or additional_data.get("instCity")
    )
    target_level = (
        additional_data.get("level")
        or additional_data.get("govtLevel")
    )

    resolved_unit = await resolve_government_unit_for_registration(
        db,
        state=target_state,
        city=target_city,
        level=target_level,
        account_type=account_type_str,
    )
    resolved_unit_id = resolved_unit.id if resolved_unit else None

    if account_type_str == "GOVERNMENT" and resolved_unit_id:
        user.government_unit_id = resolved_unit_id

    if account_type_str == "CANDIDATE":
        db.add(
            CandidateProfile(
                user_id=user.id,
                first_name=first_name,
                last_name=last_name,
                status=CandidateProfileStatus.ACTIVE.value,
                is_public=True,
            )
        )
    elif account_type_str == "EMPLOYER":
        company_name = additional_data.get("companyName") or f"{first_name}'s Enterprise"
        db.add(
            Organization(
                owner_user_id=user.id,
                government_unit_id=resolved_unit_id,
                organization_type=OrganizationType.EMPLOYER.value,
                legal_name=company_name,
                display_name=company_name,
                email=email,
                phone=phone,
                verification_status=OrganizationVerificationStatus.PENDING.value,
                is_active=True,
            )
        )
        db.add(
            VerificationApplication(
                applicant_user_id=user.id,
                government_unit_id=resolved_unit_id,
                application_type="EMPLOYER",
                status=VerificationStatus.PENDING.value,
                remarks="Initial employer statutory verification application",
            )
        )
    elif account_type_str == "TRAINING_INSTITUTE":
        inst_name = additional_data.get("instituteName") or f"{first_name} Technical Institute"
        org = Organization(
            owner_user_id=user.id,
            government_unit_id=resolved_unit_id,
            organization_type=OrganizationType.TRAINING_INSTITUTE.value,
            legal_name=inst_name,
            display_name=inst_name,
            email=email,
            phone=phone,
            verification_status=OrganizationVerificationStatus.PENDING.value,
            is_active=True,
        )
        db.add(org)
        await db.flush()
        db.add(
            InstitutionProfile(
                organization_id=org.id,
                accreditation_body=additional_data.get("affiliationBody") or "Vocational / NSDC",
                verification_status=InstitutionVerificationStatus.PENDING.value,
            )
        )
        db.add(
            VerificationApplication(
                applicant_user_id=user.id,
                government_unit_id=resolved_unit_id,
                application_type="INSTITUTION",
                status=VerificationStatus.PENDING.value,
                remarks="Initial institute statutory accreditation application",
            )
        )
    elif account_type_str == "GOVERNMENT":
        db.add(
            VerificationApplication(
                applicant_user_id=user.id,
                government_unit_id=resolved_unit_id,
                application_type="GOVERNMENT",
                status=VerificationStatus.PENDING.value,
                remarks=f"Initial government authority verification application ({target_level or 'Administrative'})",
            )
        )

    # Notify eligible government verifiers about the new verification queue entry
    if account_type_str in ("EMPLOYER", "TRAINING_INSTITUTE", "GOVERNMENT"):
        eligible_verifiers = await get_eligible_verifier_user_ids(
            db,
            target_entity_type=account_type_str,
            target_unit_id=resolved_unit_id,
        )
        notif_service = NotificationService(db)
        for verifier_id in eligible_verifiers:
            await notif_service.create_notification(
                user_id=verifier_id,
                notification_type=NotificationType.GOVERNMENT_ALERT,
                title="New Verification Application Submitted",
                message=f"New {account_type_str.replace('_', ' ').title()} application submitted for jurisdiction verification.",
                priority=NotificationPriority.HIGH,
                entity_type="VERIFICATION_APPLICATION",
                action_url="/dashboard/government",
            )
        await event_manager.broadcast_to_users(
            eligible_verifiers,
            "VERIFICATION_QUEUE_UPDATED",
            {
                "action": "NEW_APPLICATION",
                "entity_type": account_type_str,
                "government_unit_id": str(resolved_unit_id) if resolved_unit_id else None,
            },
        )

    # Mark session completed
    now = _now()
    session.completed = True
    session.completed_at = now

    # Audit log
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action=AuditAction.CREATE.value,
            resource_type="User",
            resource_id=user.id,
            description=f"User registered with {account_type_str} account via sequential dual-contact OTP",
            metadata_json={
                "account_type": account_type_str,
                "email": email,
                "phone": phone,
                "verified_via": "SEQUENTIAL_DUAL_OTP",
            },
        )
    )

    # Issue tokens
    access_token = create_access_token(
        str(user.id),
        extra_claims={
            "account_type": user.account_type,
            "roles": [role_code],
        },
    )
    refresh_token, _ = await create_auth_session(db, user)

    await db.commit()
    await db.refresh(user)

    return user, access_token, refresh_token, [role_code]
