from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import JWTError
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.models.auth_session import AuthSession
from app.models.candidate_profile import CandidateProfile, CandidateProfileStatus
from app.models.institution_profile import (
    InstitutionProfile,
    InstitutionVerificationStatus,
)
from app.models.organization import (
    Organization,
    OrganizationType,
    OrganizationVerificationStatus,
)
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.auth import AccountType, LoginRequest, SignupRequest


class AuthError(Exception):
    """Base authentication error."""


class DuplicateIdentifierError(AuthError):
    """Email or phone is already registered."""


class InvalidCredentialsError(AuthError):
    """Credentials are invalid."""


class AccountLockedError(AuthError):
    """Account is temporarily locked."""


class InactiveAccountError(AuthError):
    """Account is inactive or suspended."""


def _normalize_identifier(identifier: str) -> str:
    return identifier.strip()


def _get_phone_variations(phone: str | None) -> list[str]:
    if not phone:
        return []
    clean = re.sub(r"[\s\-\(\)]", "", phone.strip())
    variations = {clean, phone.strip()}
    digits_only = re.sub(r"\D", "", clean)
    if len(digits_only) == 10:
        variations.add(digits_only)
        variations.add(f"+91{digits_only}")
        variations.add(f"0{digits_only}")
    elif len(digits_only) == 12 and digits_only.startswith("91"):
        last10 = digits_only[2:]
        variations.add(last10)
        variations.add(f"+{digits_only}")
        variations.add(f"0{last10}")
    elif len(digits_only) == 11 and digits_only.startswith("0"):
        last10 = digits_only[1:]
        variations.add(last10)
        variations.add(f"+91{last10}")
    return list(variations)


def _hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _refresh_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )


def _default_role_for_account_type(account_type: AccountType) -> str:
    mapping = {
        AccountType.SUPER_ADMIN: "SUPER_ADMIN",
        AccountType.GOVERNMENT: "GOVERNMENT_VERIFIER",
        AccountType.EMPLOYER: "ORG_ADMIN",
        AccountType.TRAINING_INSTITUTE: "INSTITUTION_ADMIN",
        AccountType.CANDIDATE: "CANDIDATE",
    }

    return mapping[account_type]


async def signup(
    db: AsyncSession,
    data: SignupRequest,
) -> User:
    if not data.email and not data.phone:
        raise InvalidCredentialsError(
            "At least an email or phone number is required."
        )

    email = data.email.lower().strip() if data.email else None
    phone = _normalize_identifier(data.phone) if data.phone else None

    user_by_email: User | None = None
    user_by_phone: User | None = None

    if email:
        res_e = await db.execute(select(User).where(User.email == email))
        user_by_email = res_e.scalar_one_or_none()

    if phone:
        phone_variations = _get_phone_variations(phone)
        res_p = await db.execute(select(User).where(User.phone.in_(phone_variations)))
        user_by_phone = res_p.scalar_one_or_none()

    # Prevent account merging/takeover when email and phone belong to different accounts
    if user_by_email and user_by_phone and user_by_email.id != user_by_phone.id:
        raise DuplicateIdentifierError(
            "Email and phone number belong to different existing accounts."
        )

    # If the email is already registered and verified, reject with 409
    if user_by_email and user_by_email.email_verified:
        raise DuplicateIdentifierError("Email already registered")

    # If the phone is already registered and verified, reject with 409
    if user_by_phone and user_by_phone.phone_verified:
        raise DuplicateIdentifierError("Phone already registered")

    # If phone belongs to an existing user whose email is different, reject with 409
    if user_by_phone and email and user_by_phone.email and user_by_phone.email != email:
        raise DuplicateIdentifierError("Phone already registered")

    # If email belongs to an existing user whose phone is different, reject with 409
    if user_by_email and phone and user_by_email.phone and user_by_email.phone not in _get_phone_variations(phone):
        raise DuplicateIdentifierError("Email already registered")

    existing_user = user_by_email or user_by_phone

    if existing_user is not None:
        # Existing unverified account must require correct password verification
        if not verify_password(data.password, existing_user.password_hash):
            raise InvalidCredentialsError(
                "Incorrect password for existing unverified account."
            )

        # Update contact info if missing on existing account
        if email and not existing_user.email:
            existing_user.email = email
        if phone and not existing_user.phone:
            existing_user.phone = phone
        if getattr(data, "username", None) and not existing_user.username:
            existing_user.username = data.username.lower().strip()

        existing_user.account_type = data.account_type.value

        await _provision_account_profile(db, existing_user, data)

        await db.commit()
        await db.refresh(existing_user)
        return existing_user

    clean_uname = data.username.lower().strip() if getattr(data, "username", None) else None
    user = User(
        email=email,
        phone=phone,
        username=clean_uname,
        password_hash=hash_password(data.password),
        account_type=data.account_type.value,
        email_verified=False,
        phone_verified=False,
        password_changed_at=datetime.now(timezone.utc),
    )

    db.add(user)
    await db.flush()

    role_code = _default_role_for_account_type(
        data.account_type
    )

    role_result = await db.execute(
        select(Role).where(
            Role.code == role_code,
            Role.is_active.is_(True),
        )
    )

    role = role_result.scalar_one_or_none()

    if role is None:
        raise AuthError(
            f"Required role '{role_code}' does not exist."
        )

    user_role = UserRole(
        user_id=user.id,
        role_id=role.id,
    )

    db.add(user_role)

    await _provision_account_profile(db, user, data)

    await db.commit()
    await db.refresh(user)

    return user


async def _provision_account_profile(
    db: AsyncSession,
    user: User,
    data: SignupRequest,
) -> None:
    """
    Ensure the appropriate entity (CandidateProfile or Organization) exists
    for the newly created or updated user account.
    """
    if data.account_type == AccountType.CANDIDATE:
        cp_res = await db.execute(
            select(CandidateProfile).where(CandidateProfile.user_id == user.id)
        )
        if not cp_res.scalar_one_or_none():
            raw_name = (data.fullName or "").strip()
            if raw_name:
                parts = raw_name.split(" ", 1)
                first_name = parts[0]
                last_name = parts[1] if len(parts) > 1 else ""
            else:
                first_name = (user.email.split("@")[0] if user.email else "Candidate").capitalize()
                last_name = ""

            db.add(
                CandidateProfile(
                    user_id=user.id,
                    first_name=first_name,
                    last_name=last_name,
                    status=CandidateProfileStatus.ACTIVE.value,
                    is_public=True,
                )
            )

    elif data.account_type in (AccountType.EMPLOYER, AccountType.TRAINING_INSTITUTE):
        org_res = await db.execute(
            select(Organization).where(Organization.owner_user_id == user.id)
        )
        existing_org = org_res.scalar_one_or_none()
        org_type = (
            OrganizationType.EMPLOYER.value
            if data.account_type == AccountType.EMPLOYER
            else OrganizationType.TRAINING_INSTITUTE.value
        )
        if not existing_org:
            legal_name = (
                data.companyName
                or data.instituteName
                or data.fullName
                or f"{org_type.replace('_', ' ').title()} Organization"
            ).strip()

            org = Organization(
                owner_user_id=user.id,
                organization_type=org_type,
                legal_name=legal_name,
                display_name=legal_name,
                verification_status=OrganizationVerificationStatus.PENDING.value,
                is_active=True,
            )
            db.add(org)
            await db.flush()

            if data.account_type == AccountType.TRAINING_INSTITUTE:
                inst_res = await db.execute(
                    select(InstitutionProfile).where(InstitutionProfile.organization_id == org.id)
                )
                if not inst_res.scalar_one_or_none():
                    db.add(
                        InstitutionProfile(
                            organization_id=org.id,
                            verification_status=InstitutionVerificationStatus.PENDING.value,
                        )
                    )


async def create_auth_session(
    db: AsyncSession,
    user: User,
) -> tuple[str, AuthSession]:
    """
    Create a new refresh-token session.

    The refresh JWT itself contains a unique `jti`, generated by
    create_refresh_token(), so multiple tokens generated for the
    same user cannot collide.
    """

    refresh_token = create_refresh_token(
        str(user.id),
        extra_claims={
            "account_type": user.account_type,
        },
    )

    session = AuthSession(
        user_id=user.id,
        refresh_token_hash=_hash_refresh_token(
            refresh_token
        ),
        expires_at=_refresh_expiry(),
        revoked=False,
    )

    db.add(session)

    return refresh_token, session


_create_auth_session = create_auth_session


async def login(
    db: AsyncSession,
    data: LoginRequest,
) -> tuple[User, str, str, list[str]]:
    raw_ident = _normalize_identifier(data.identifier)
    ident_lower = raw_ident.lower()
    clean_username = raw_ident.lstrip("@").strip().lower()
    phone_variations = _get_phone_variations(raw_ident)

    conditions = [
        User.email == ident_lower,
        func.lower(User.username) == clean_username,
    ]
    if phone_variations:
        conditions.append(User.phone.in_(phone_variations))
    elif raw_ident:
        conditions.append(User.phone == raw_ident)

    result = await db.execute(
        select(User).where(or_(*conditions))
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise InvalidCredentialsError(
            "Invalid credentials."
        )

    now = datetime.now(timezone.utc)

    if user.locked_until is not None:
        locked_until = user.locked_until

        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(
                tzinfo=timezone.utc
            )

        if locked_until > now:
            raise AccountLockedError(
                "Account is temporarily locked. "
                "Please try again later."
            )

        user.locked_until = None
        user.failed_login_attempts = 0

    if not user.is_active or user.is_suspended:
        raise InactiveAccountError(
            "Account is inactive or suspended."
        )

    if not user.email_verified and not user.phone_verified:
        raise InactiveAccountError(
            "Account is unverified. Please complete account verification before signing in."
        )

    if not verify_password(
        data.password,
        user.password_hash,
    ):
        user.failed_login_attempts += 1

        if (
            user.failed_login_attempts
            >= settings.MAX_LOGIN_ATTEMPTS
        ):
            user.locked_until = (
                now
                + timedelta(
                    minutes=settings.ACCOUNT_LOCKOUT_MINUTES
                )
            )

        await db.commit()

        raise InvalidCredentialsError(
            "Invalid credentials."
        )

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now

    role_result = await db.execute(
        select(Role.code)
        .join(
            UserRole,
            UserRole.role_id == Role.id,
        )
        .where(
            UserRole.user_id == user.id,
            UserRole.revoked_at.is_(None),
            Role.is_active.is_(True),
        )
        .order_by(Role.code),
    )

    roles = list(
        role_result.scalars().all()
    )

    access_token = create_access_token(
        str(user.id),
        extra_claims={
            "account_type": user.account_type,
            "roles": roles,
        },
    )

    refresh_token, _session = (
        await _create_auth_session(
            db,
            user,
        )
    )

    await db.commit()

    return (
        user,
        access_token,
        refresh_token,
        roles,
    )


async def refresh_access_token(
    db: AsyncSession,
    refresh_token: str,
) -> tuple[User, str, str, list[str]]:
    """
    Validate and rotate a refresh token.

    Security checks:
    1. JWT signature/type/expiry are valid.
    2. JWT contains a valid subject.
    3. The corresponding database session exists.
    4. The database session has not been revoked.
    5. The JWT subject matches the session user.
    6. The database session has not expired.
    7. The user still exists and is active.
    8. The old session is revoked before creating the new session.
    """

    # ---------------------------------------------------------
    # 1. Validate the JWT itself.
    # ---------------------------------------------------------
    try:
        payload = decode_refresh_token(
            refresh_token
        )
    except (
        JWTError,
        ValueError,
        TypeError,
    ) as exc:
        raise InvalidCredentialsError(
            "Invalid or expired refresh token."
        ) from exc

    user_id_raw = payload.get("sub")

    if not user_id_raw:
        raise InvalidCredentialsError(
            "Refresh token subject is missing."
        )

    try:
        token_user_id = UUID(
            str(user_id_raw)
        )
    except (
        ValueError,
        TypeError,
    ) as exc:
        raise InvalidCredentialsError(
            "Refresh token subject is invalid."
        ) from exc

    # ---------------------------------------------------------
    # 2. Find the matching database session.
    # ---------------------------------------------------------
    token_hash = _hash_refresh_token(
        refresh_token
    )

    result = await db.execute(
        select(AuthSession).where(
            AuthSession.refresh_token_hash
            == token_hash,
            AuthSession.revoked.is_(False),
        )
    )

    session = result.scalar_one_or_none()

    if session is None:
        raise InvalidCredentialsError(
            "Invalid or revoked refresh token."
        )

    # ---------------------------------------------------------
    # 3. Make sure JWT subject and DB session agree.
    # ---------------------------------------------------------
    if session.user_id != token_user_id:
        raise InvalidCredentialsError(
            "Refresh token does not match the session."
        )

    now = datetime.now(timezone.utc)

    # ---------------------------------------------------------
    # 4. Check database session expiry.
    # ---------------------------------------------------------
    expires_at = session.expires_at

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(
            tzinfo=timezone.utc
        )

    if expires_at <= now:
        session.revoked = True
        session.revoked_at = now

        await db.commit()

        raise InvalidCredentialsError(
            "Refresh token has expired."
        )

    # ---------------------------------------------------------
    # 5. Load user.
    # ---------------------------------------------------------
    user = await db.get(
        User,
        session.user_id,
    )

    if user is None:
        session.revoked = True
        session.revoked_at = now

        await db.commit()

        raise InvalidCredentialsError(
            "User account no longer exists."
        )

    # ---------------------------------------------------------
    # 6. Check account status.
    # ---------------------------------------------------------
    if not user.is_active or user.is_suspended:
        raise InactiveAccountError(
            "Account is inactive or suspended."
        )

    # ---------------------------------------------------------
    # 7. Get current active roles.
    # ---------------------------------------------------------
    role_result = await db.execute(
        select(Role.code)
        .join(
            UserRole,
            UserRole.role_id == Role.id,
        )
        .where(
            UserRole.user_id == user.id,
            UserRole.revoked_at.is_(None),
            Role.is_active.is_(True),
        )
        .order_by(Role.code),
    )

    roles = list(
        role_result.scalars().all()
    )

    # ---------------------------------------------------------
    # 8. Revoke old refresh session.
    # ---------------------------------------------------------
    session.revoked = True
    session.revoked_at = now

    # ---------------------------------------------------------
    # 9. Create a new access token.
    # ---------------------------------------------------------
    access_token = create_access_token(
        str(user.id),
        extra_claims={
            "account_type": user.account_type,
            "roles": roles,
        },
    )

    # ---------------------------------------------------------
    # 10. Create a new refresh token/session.
    #
    # create_refresh_token() must generate a unique `jti`.
    # ---------------------------------------------------------
    new_refresh_token, _new_session = (
        await _create_auth_session(
            db,
            user,
        )
    )

    await db.commit()

    return (
        user,
        access_token,
        new_refresh_token,
        roles,
    )


async def revoke_refresh_token(
    db: AsyncSession,
    refresh_token: str,
) -> bool:
    """
    Revoke a refresh-token session.

    Returns:
        True  -> token/session was found and revoked.
        False -> token/session was not found or already revoked.
    """

    # Validate that the supplied value is actually a
    # properly signed refresh JWT before looking up its hash.
    try:
        payload = decode_refresh_token(
            refresh_token
        )
    except (
        JWTError,
        ValueError,
        TypeError,
    ):
        return False

    user_id_raw = payload.get("sub")

    if not user_id_raw:
        return False

    try:
        token_user_id = UUID(
            str(user_id_raw)
        )
    except (
        ValueError,
        TypeError,
    ):
        return False

    token_hash = _hash_refresh_token(
        refresh_token
    )

    result = await db.execute(
        select(AuthSession).where(
            AuthSession.refresh_token_hash
            == token_hash,
            AuthSession.revoked.is_(False),
        )
    )

    session = result.scalar_one_or_none()

    if session is None:
        return False

    if session.user_id != token_user_id:
        return False

    session.revoked = True
    session.revoked_at = (
        datetime.now(timezone.utc)
    )

    await db.commit()

    return True


async def get_user_by_id(
    db: AsyncSession,
    user_id: UUID,
) -> User | None:
    return await db.get(
        User,
        user_id,
    )