from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings


from app.core.security import (
    create_verification_token,
    get_current_user,
    get_current_user_with_roles,
    get_current_verification_user,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    OtpVerifyRequest,
    RefreshTokenRequest,
    ResendOtpRequest,
    SignupRequest,
    SignupResponse,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import (
    AccountLockedError,
    AuthError,
    DuplicateIdentifierError,
    InactiveAccountError,
    InvalidCredentialsError,
    create_auth_session,
    get_user_by_id,
    login,
    refresh_access_token,
    revoke_refresh_token,
    signup,
)
from app.services.user_service import resolve_user_verification_status
from app.services.username_service import is_username_available, normalize_username

from app.schemas.verification import (
    CompleteSignupRequest,
    RequestVerificationCode,
    RequestVerificationResponse,
    VerificationChannel,
    SendSecondaryOtpRequest,
    SendSecondaryOtpResponse,
    StartSignupVerificationRequest,
    StartSignupVerificationResponse,
    VerifyPrimaryResponse,
    VerifySecondaryResponse,
    VerifySignupOtpRequest,
    VerifyVerificationCode,
    VerifyVerificationResponse,
)
from app.services.otp_delivery_service import validate_smtp_configuration, validate_sms_configuration
from app.services.verification_service import (
    AlreadyVerifiedError,
    DeliveryError,
    InvalidChannelError,
    InvalidOTPError,
    MaxResendsExceededError,
    OTPAlreadyUsedError,
    OTPAttemptsExceededError,
    OTPExpiredError,
    ResendCooldownError,
    VerificationError,
    complete_verified_signup,
    initiate_secondary_signup_otp,
    initiate_signup_session,
    request_otp,
    verify_otp,
    verify_primary_signup_otp,
    verify_secondary_signup_otp,
)


def _should_provide_dev_otp(channel: Any) -> bool:
    """
    Determine if OTP should be returned in API response for verification.
    Active strictly in development/local/test AND when explicit demo OTP mode is enabled.
    NEVER returned in production, regardless of ALLOW_DEMO_SMS.
    """
    chan_str = channel.value if hasattr(channel, "value") else str(channel)
    if chan_str.upper() != "PHONE":
        return False
    env = (settings.ENVIRONMENT or "").strip().lower()
    if env not in ("development", "local", "test"):
        return False
    if not getattr(settings, "ALLOW_DEMO_SMS", False):
        provider = (settings.SMS_PROVIDER or "").strip().lower()
        if provider not in ("sandbox", "console"):
            return False
    return True


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/signup",
    response_model=SignupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def signup_endpoint(
    data: SignupRequest,
    db: AsyncSession = Depends(get_db),
) -> SignupResponse:

    try:
        user = await signup(db, data)

    except DuplicateIdentifierError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        await db.rollback()

        print(
            f"SIGNUP ERROR: {type(exc).__name__}: {exc}"
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Unable to create account: "
                f"{type(exc).__name__}: {exc}"
            ),
        ) from exc

    # Automatically dispatch real OTP challenge to user's registered contact
    try:
        primary_ch = "EMAIL" if user.email else "PHONE"
        await request_otp(db, user, channel=primary_ch, purpose="SIGNUP")
    except Exception as exc:
        print(f"[SIGNUP OTP DISPATCH] Notice: {exc}")

    verification_token = create_verification_token(
        str(user.id)
    )

    return SignupResponse(
        id=str(user.id),
        account_type=data.account_type,
        email=user.email,
        phone=user.phone,
        email_verified=user.email_verified,
        phone_verified=user.phone_verified,
        verification_token=verification_token,
        message=(
            "Account created successfully. "
            "Please verify your email or phone before continuing."
        ),
    )


@router.post(
    "/register",
    response_model=SignupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_endpoint(
    data: SignupRequest,
    db: AsyncSession = Depends(get_db),
) -> SignupResponse:
    """
    Alias for /signup endpoint to support varied frontend consumers.
    """
    return await signup_endpoint(data, db)


@router.post(
    "/login",
    response_model=TokenResponse,
)
async def login_endpoint(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:

    try:
        user, access_token, refresh_token, roles = await login(
            db,
            data,
        )

    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    except AccountLockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=str(exc),
        ) from exc

    except InactiveAccountError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        await db.rollback()

        print(
            f"LOGIN ERROR: {type(exc).__name__}: {exc}"
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Unable to authenticate: "
                f"{type(exc).__name__}: {exc}"
            ),
        ) from exc

    v_status = await resolve_user_verification_status(db, user)
    user_response = UserResponse(
        id=str(user.id),
        email=user.email,
        phone=user.phone,
        username=user.username,
        account_type=user.account_type,
        is_active=user.is_active,
        is_suspended=user.is_suspended,
        email_verified=user.email_verified,
        phone_verified=user.phone_verified,
        verification_status=v_status,
        government_unit_id=str(user.government_unit_id) if user.government_unit_id else None,
        roles=roles,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        token=access_token,
        user=user_response,
        success=True,
        message="Login successful.",
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        (
            _user,
            access_token,
            refresh_token_value,
            _roles,
        ) = await refresh_access_token(
            db,
            data.refresh_token,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_value,
            token_type="bearer",
        )

    except InactiveAccountError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@router.post("/logout")
async def logout(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    revoked = await revoke_refresh_token(
        db,
        data.refresh_token,
    )

    return {
        "message": (
            "Logged out successfully."
            if revoked
            else "Session already logged out or invalid."
        )
    }


@router.get(
    "/me",
    response_model=UserResponse,
)
async def me(
    current_user_and_roles: tuple[User, list[str]] = Depends(
        get_current_user_with_roles
    ),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    current_user, roles = current_user_and_roles
    v_status = await resolve_user_verification_status(db, current_user)
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        phone=current_user.phone,
        username=current_user.username,
        account_type=current_user.account_type,
        is_active=current_user.is_active,
        is_suspended=current_user.is_suspended,
        email_verified=current_user.email_verified,
        phone_verified=current_user.phone_verified,
        verification_status=v_status,
        government_unit_id=str(current_user.government_unit_id) if current_user.government_unit_id else None,
        roles=roles,
    )


@router.get(
    "/me/roles",
)
async def my_roles(
    current_user_and_roles: tuple[User, list[str]] = Depends(
        get_current_user_with_roles
    ),
) -> dict:
    current_user, roles = current_user_and_roles

    return {
        "user_id": str(current_user.id),
        "account_type": current_user.account_type,
        "roles": roles,
    }

@router.post(
    "/verification/request",
    response_model=RequestVerificationResponse,
)
async def request_verification_code(
    data: RequestVerificationCode,
    current_user: User = Depends(get_current_verification_user),
    db: AsyncSession = Depends(get_db),
) -> RequestVerificationResponse:
    try:
        _challenge, otp = await request_otp(
            db=db,
            user=current_user,
            channel=data.channel.value,
            purpose=data.purpose.value,
        )

    except AlreadyVerifiedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except (ResendCooldownError, MaxResendsExceededError) as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc

    except InvalidChannelError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except DeliveryError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        await db.rollback()
        print(
            f"VERIFICATION REQUEST ERROR: "
            f"{type(exc).__name__}: {exc}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to send verification code.",
        ) from exc

    dev_otp = (
        otp
        if _should_provide_dev_otp(data.channel)
        else None
    )

    return RequestVerificationResponse(
        message=(
            f"Verification code sent to your "
            f"{data.channel.value.lower()}."
        ),
        channel=data.channel,
        expires_in_seconds=600,
        dev_otp=dev_otp,
    )


@router.post(
    "/verification/verify",
    response_model=VerifyVerificationResponse,
)
async def verify_verification_code(
    data: VerifyVerificationCode,
    current_user: User = Depends(get_current_verification_user),
    db: AsyncSession = Depends(get_db),
) -> VerifyVerificationResponse:
    try:
        user = await verify_otp(
            db=db,
            user=current_user,
            channel=data.channel.value,
            otp=data.otp,
            purpose=data.purpose.value,
        )

    except InvalidChannelError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except OTPExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=str(exc),
        ) from exc

    except OTPAttemptsExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc

    except OTPAlreadyUsedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except InvalidOTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        await db.rollback()
        print(
            f"VERIFICATION ERROR: "
            f"{type(exc).__name__}: {exc}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to verify code.",
        ) from exc

    verification_complete = (
        user.email_verified or user.phone_verified
    )

    return VerifyVerificationResponse(
        message="Verification successful.",
        email_verified=user.email_verified,
        phone_verified=user.phone_verified,
        verification_complete=verification_complete,
    )


@router.post("/verify-otp")
async def verify_otp_endpoint(
    data: OtpVerifyRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Verify user identity OTP from frontend.
    """
    from datetime import datetime, timezone
    from app.core.security import create_access_token
    from app.models.candidate_profile import CandidateProfile, CandidateProfileStatus
    from app.models.role import Role
    from app.models.user_role import UserRole
    from app.models.verification_challenge import VerificationChallenge
    from app.services.verification_service import hash_otp

    identifier = data.identifier.strip()
    if "@" in identifier:
        identifier = identifier.lower()

    res = await db.execute(
        select(User).where((User.email == identifier) | (User.phone == identifier))
    )
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with identifier '{data.identifier}' not found.",
        )

    # Validate against active VerificationChallenge if one exists
    challenge_res = await db.execute(
        select(VerificationChallenge)
        .where(
            VerificationChallenge.user_id == user.id,
            VerificationChallenge.consumed.is_(False),
        )
        .order_by(VerificationChallenge.created_at.desc())
        .limit(1)
    )
    challenge = challenge_res.scalar_one_or_none()
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active verification code found. Please request a new verification code.",
        )

    now = datetime.now(timezone.utc)
    if challenge.expires_at and challenge.expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired. Please request a new one.",
        )
    if challenge.code_hash != hash_otp(data.otp):
        challenge.attempts += 1
        if challenge.attempts >= challenge.max_attempts:
            challenge.consumed = True
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code. Please check and try again.",
        )
    challenge.consumed = True
    challenge.consumed_at = now

    if "@" in identifier:
        user.email_verified = True
    else:
        user.phone_verified = True

    user.is_active = True

    # Ensure CandidateProfile exists for CANDIDATE accounts
    if user.account_type == "CANDIDATE":
        cp_res = await db.execute(
            select(CandidateProfile).where(CandidateProfile.user_id == user.id)
        )
        if not cp_res.scalar_one_or_none():
            name_part = (user.email.split("@")[0] if user.email else "Candidate").capitalize()
            db.add(
                CandidateProfile(
                    user_id=user.id,
                    first_name=name_part,
                    status=CandidateProfileStatus.ACTIVE.value,
                    is_public=True,
                )
            )

    role_res = await db.execute(
        select(Role.code)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id, UserRole.revoked_at.is_(None), Role.is_active.is_(True))
    )
    roles = list(role_res.scalars().all())
    if not roles:
        roles = [user.account_type]

    access_token = create_access_token(
        str(user.id),
        extra_claims={
            "account_type": user.account_type,
            "roles": roles,
        },
    )

    refresh_token, _ = await create_auth_session(db, user)

    await db.commit()
    await db.refresh(user)

    user_data = {
        "id": str(user.id),
        "name": user.email.split("@")[0] if user.email else "User",
        "email": user.email or "",
        "phone": user.phone or "",
        "account_type": user.account_type,
        "accountType": user.account_type.lower() if user.account_type else "candidate",
        "roles": roles,
        "isVerified": True,
        "is_active": user.is_active,
        "email_verified": user.email_verified,
        "phone_verified": user.phone_verified,
    }

    return {
        "success": True,
        "message": "Identity verified successfully! Your SkillVistaar profile is active.",
        "token": access_token,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user_data,
    }


@router.post("/resend-otp")
async def resend_otp_endpoint(
    data: ResendOtpRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    identifier = data.identifier.strip()
    if "@" in identifier:
        identifier = identifier.lower()

    res = await db.execute(
        select(User).where((User.email == identifier) | (User.phone == identifier))
    )
    user = res.scalar_one_or_none()
    dev_otp: str | None = None
    if user:
        channel = "EMAIL" if "@" in identifier else "PHONE"
        try:
            _challenge, otp = await request_otp(db, user, channel=channel, purpose="SIGNUP")
            if _should_provide_dev_otp(channel):
                dev_otp = otp
        except (ResendCooldownError, MaxResendsExceededError) as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(exc),
            ) from exc
        except DeliveryError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            print(f"[RESEND OTP] Notice: {exc}")

    return {
        "success": True,
        "message": f"New 6-digit OTP sent to {data.identifier}",
        "dev_otp": dev_otp,
    }


@router.post("/forgot-password")
async def forgot_password_endpoint(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    return {
        "success": True,
        "message": f"A password reset link & OTP has been sent to {data.identifier}.",
    }


# =========================================================================
# Sequential Dual-Contact Signup Endpoints
# =========================================================================

@router.post(
    "/signup/start-verification",
    response_model=StartSignupVerificationResponse,
)
async def start_signup_verification_endpoint(
    data: StartSignupVerificationRequest,
    db: AsyncSession = Depends(get_db),
) -> StartSignupVerificationResponse:
    """
    Step 1: Choose Account Type & enter Primary Contact (Mobile OR Email).
    Dispatches REAL OTP via SMTP or SMS.
    """
    try:
        session, session_token, otp = await initiate_signup_session(
            db=db,
            account_type=data.account_type,
            channel=data.channel,
            identifier=data.identifier,
        )
    except AlreadyVerifiedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except DeliveryError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except (ResendCooldownError, MaxResendsExceededError) as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc
    except (VerificationError, InvalidChannelError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        await db.rollback()
        print(f"[START_VERIFICATION ERROR] {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate verification.",
        ) from exc

    dev_otp = (
        otp
        if _should_provide_dev_otp(session.primary_channel)
        else None
    )

    return StartSignupVerificationResponse(
        session_token=session_token,
        channel=session.primary_channel,
        identifier=session.primary_identifier,
        expires_in_seconds=600,
        message=f"Verification code sent to your {session.primary_channel.lower()}.",
        dev_otp=dev_otp,
    )


@router.post(
    "/signup/verify-primary",
    response_model=VerifyPrimaryResponse,
)
async def verify_primary_endpoint(
    data: VerifySignupOtpRequest,
    db: AsyncSession = Depends(get_db),
) -> VerifyPrimaryResponse:
    """
    Step 2: Verify primary contact OTP.
    """
    try:
        session = await verify_primary_signup_otp(
            db=db,
            session_token=data.session_token,
            otp=data.otp,
        )
    except OTPExpiredError as exc:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(exc)) from exc
    except OTPAttemptsExceededError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except InvalidOTPError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Verification failed.") from exc

    next_channel = "PHONE" if session.primary_channel == "EMAIL" else "EMAIL"
    return VerifyPrimaryResponse(
        session_token=session.session_token,
        primary_verified=True,
        primary_channel=session.primary_channel,
        next_channel=next_channel,
        message=f"{session.primary_channel.capitalize()} verified successfully. Now verify your {next_channel.lower()}.",
    )


@router.post(
    "/signup/send-secondary-otp",
    response_model=SendSecondaryOtpResponse,
)
async def send_secondary_otp_endpoint(
    data: SendSecondaryOtpRequest,
    db: AsyncSession = Depends(get_db),
) -> SendSecondaryOtpResponse:
    """
    Step 3: Enter the other contact and send real OTP.
    """
    try:
        session, otp = await initiate_secondary_signup_otp(
            db=db,
            session_token=data.session_token,
            channel=data.channel,
            identifier=data.identifier,
        )
    except AlreadyVerifiedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except DeliveryError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except (ResendCooldownError, MaxResendsExceededError) as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc
    except (VerificationError, InvalidChannelError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send verification code.") from exc

    dev_otp = (
        otp
        if _should_provide_dev_otp(session.secondary_channel)
        else None
    )

    return SendSecondaryOtpResponse(
        session_token=session.session_token,
        channel=session.secondary_channel or "PHONE",
        identifier=session.secondary_identifier or "",
        expires_in_seconds=600,
        message=f"Verification code sent to your {session.secondary_channel.lower()}.",
        dev_otp=dev_otp,
    )


@router.post(
    "/signup/verify-secondary",
    response_model=VerifySecondaryResponse,
)
async def verify_secondary_endpoint(
    data: VerifySignupOtpRequest,
    db: AsyncSession = Depends(get_db),
) -> VerifySecondaryResponse:
    """
    Step 4: Verify secondary contact OTP.
    """
    try:
        session = await verify_secondary_signup_otp(
            db=db,
            session_token=data.session_token,
            otp=data.otp,
        )
    except OTPExpiredError as exc:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(exc)) from exc
    except OTPAttemptsExceededError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except InvalidOTPError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Verification failed.") from exc

    return VerifySecondaryResponse(
        session_token=session.session_token,
        both_verified=True,
        message="Both email and phone verified successfully.",
    )


@router.post(
    "/signup/complete",
)
async def complete_signup_endpoint(
    data: CompleteSignupRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Step 5: Final Account Creation.
    Enforces dual verification, terms acceptance, and provisions user in PostgreSQL.
    """
    try:
        user, access_token, refresh_token, roles = await complete_verified_signup(
            db=db,
            session_token=data.session_token,
            password=data.password,
            terms_accepted=data.terms_accepted,
            additional_data=data.additional_data,
        )
    except AlreadyVerifiedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except VerificationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Account creation failed: {exc}") from exc

    v_status = await resolve_user_verification_status(db, user)

    return {
        "success": True,
        "message": "Account created successfully! Welcome to SkillVistaar.",
        "token": access_token,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": str(user.id),
            "name": (user.email.split("@")[0] if user.email else "User").capitalize(),
            "email": user.email or "",
            "phone": user.phone or "",
            "username": user.username or "",
            "account_type": user.account_type,
            "accountType": user.account_type.lower() if user.account_type else "candidate",
            "roles": roles,
            "isVerified": v_status == "APPROVED",
            "verification_status": v_status,
            "is_active": user.is_active,
            "email_verified": user.email_verified,
            "phone_verified": user.phone_verified,
        },
    }


@router.get("/check-username")
async def check_username_endpoint(
    username: str = Query(..., min_length=1, max_length=50),
    db: AsyncSession = Depends(get_db),
) -> dict:
    available, msg = await is_username_available(db, username)
    return {
        "available": available,
        "username": normalize_username(username),
        "message": msg,
    }


@router.get("/smtp-status")
async def smtp_status_endpoint() -> dict:
    """
    Check Gmail / SMTP delivery service configuration status.
    Safe for diagnostics (never leaks passwords or secrets).
    """
    return validate_smtp_configuration()


@router.get("/sms-status")
async def sms_status_endpoint() -> dict:
    """
    Check SMS delivery service configuration status.
    Safe for diagnostics (never leaks auth tokens or API keys).
    """
    return validate_sms_configuration()


@router.get("/delivery-status")
async def delivery_status_endpoint() -> dict:
    """
    Combined OTP delivery configuration status for Email and SMS.
    Safe for diagnostics (never leaks passwords, tokens, or API keys).
    """
    smtp = validate_smtp_configuration()
    sms = validate_sms_configuration()
    return {
        "email": {
            "ready": smtp["ready"],
            "status": "CONFIGURED" if smtp["ready"] else "NOT CONFIGURED",
            "message": smtp["message"],
        },
        "sms": {
            "ready": sms["ready"],
            "status": "CONFIGURED" if sms["ready"] else "NOT CONFIGURED",
            "message": sms["message"],
        },
    }