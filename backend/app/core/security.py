from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import Depends, HTTPException, status
from fastapi.security import (
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole


# ============================================================
# Password Security
# ============================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    return pwd_context.verify(
        plain_password,
        hashed_password,
    )


def validate_password_strength(password: str) -> None:
    minimum_length = max(
        settings.PASSWORD_MIN_LENGTH,
        8,
    )

    if len(password) < minimum_length:
        raise ValueError(
            f"Password must contain at least "
            f"{minimum_length} characters."
        )

    if len(password) > 128:
        raise ValueError(
            "Password must not exceed 128 characters."
        )

    if not any(char.isupper() for char in password):
        raise ValueError(
            "Password must contain at least one uppercase letter."
        )

    if not any(char.islower() for char in password):
        raise ValueError(
            "Password must contain at least one lowercase letter."
        )

    if not any(char.isdigit() for char in password):
        raise ValueError(
            "Password must contain at least one digit."
        )

    if not any(
        not char.isalnum()
        for char in password
    ):
        raise ValueError(
            "Password must contain at least one special character."
        )


# ============================================================
# OAuth2
# ============================================================

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login"
)


# ============================================================
# JWT Creation
# ============================================================

def _build_token(
    *,
    user_id: UUID | str,
    token_type: str,
    secret_key: str,
    expires_delta: timedelta,
    extra_claims: dict | None = None,
) -> str:
    """
    Build a signed JWT.

    Every token receives a unique JWT ID (jti).
    This prevents two tokens generated in the same second
    from becoming identical.
    """

    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    payload: dict = {
        "sub": str(user_id),
        "type": token_type,
        "jti": str(uuid4()),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        secret_key,
        algorithm=settings.ALGORITHM,
    )


def create_access_token(
    user_id: UUID | str,
    expires_delta: timedelta | None = None,
    extra_claims: dict | None = None,
) -> str:
    if expires_delta is None:
        expires_delta = timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    return _build_token(
        user_id=user_id,
        token_type="access",
        secret_key=settings.SECRET_KEY,
        expires_delta=expires_delta,
        extra_claims=extra_claims,
    )


def decode_access_token(token: str) -> dict:
    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
    )

    if payload.get("type") != "access":
        raise JWTError("Invalid token type.")

    if not payload.get("sub"):
        raise JWTError("Token subject is missing.")

    if not payload.get("jti"):
        raise JWTError("Token ID is missing.")

    return payload


# ============================================================
# Verification Token
# ============================================================

VERIFICATION_TOKEN_EXPIRE_MINUTES = 15


def create_verification_token(
    user_id: UUID | str,
) -> str:
    """
    Create a short-lived JWT used only during account verification.

    This token is deliberately different from access and refresh
    tokens. It cannot be used to authenticate normal API requests.
    """

    return _build_token(
        user_id=user_id,
        token_type="verification",
        secret_key=settings.SECRET_KEY,
        expires_delta=timedelta(
            minutes=VERIFICATION_TOKEN_EXPIRE_MINUTES
        ),
        extra_claims={
            "purpose": "SIGNUP",
        },
    )


def decode_verification_token(token: str) -> dict:
    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
    )

    if payload.get("type") != "verification":
        raise JWTError("Invalid verification token type.")

    if payload.get("purpose") != "SIGNUP":
        raise JWTError("Invalid verification token purpose.")

    if not payload.get("sub"):
        raise JWTError("Verification token subject is missing.")

    if not payload.get("jti"):
        raise JWTError("Verification token ID is missing.")

    return payload

def create_refresh_token(
    user_id: UUID | str,
    expires_delta: timedelta | None = None,
    extra_claims: dict | None = None,
) -> str:
    if expires_delta is None:
        expires_delta = timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

    return _build_token(
        user_id=user_id,
        token_type="refresh",
        secret_key=settings.REFRESH_SECRET_KEY,
        expires_delta=expires_delta,
        extra_claims=extra_claims,
    )


def decode_refresh_token(token: str) -> dict:
    payload = jwt.decode(
        token,
        settings.REFRESH_SECRET_KEY,
        algorithms=[settings.ALGORITHM],
    )

    if payload.get("type") != "refresh":
        raise JWTError("Invalid token type.")

    if not payload.get("sub"):
        raise JWTError("Token subject is missing.")

    if not payload.get("jti"):
        raise JWTError("Token ID is missing.")

    return payload

# ============================================================
# Current User From Verification Token
# ============================================================

verification_bearer = HTTPBearer(
    auto_error=True,
)


async def get_current_verification_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        verification_bearer
    ),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Authenticate a newly-created account using its short-lived
    verification token.

    Only tokens with:
        type = verification
        purpose = SIGNUP

    are accepted here.

    Access and refresh tokens are rejected.
    """

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid verification credentials.",
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )

    token = credentials.credentials

    try:
        payload = decode_verification_token(token)

        user_id_raw = payload.get("sub")

        if not user_id_raw:
            raise credentials_exception

        user_id = UUID(str(user_id_raw))

    except (
        JWTError,
        ValueError,
        TypeError,
    ) as exc:
        raise credentials_exception from exc

    result = await db.execute(
        select(User).where(
            User.id == user_id
        )
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    if user.is_suspended:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is suspended.",
        )

    return user


# ============================================================
# Authentication Exception
# ============================================================

def _authentication_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate authentication credentials.",
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )


# ============================================================
# Current User
# ============================================================

async def _get_user_from_token(
    token: str,
    db: AsyncSession,
) -> User:
    credentials_exception = _authentication_exception()

    try:
        payload = decode_access_token(token)

        user_id_raw = payload.get("sub")

        if not user_id_raw:
            raise credentials_exception

        user_id = UUID(str(user_id_raw))

    except (
        JWTError,
        ValueError,
        TypeError,
    ) as exc:
        raise credentials_exception from exc

    result = await db.execute(
        select(User).where(
            User.id == user_id
        )
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    if user.is_suspended:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is suspended.",
        )

    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await _get_user_from_token(
        token=token,
        db=db,
    )


# ============================================================
# Optional Current User
# ============================================================

async def get_optional_current_user(
    token: str | None = Depends(
        OAuth2PasswordBearer(
            tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
            auto_error=False,
        )
    ),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    Return the authenticated user when a valid access token
    is supplied.

    Unlike get_current_user(), this dependency does not reject
    requests that do not contain an Authorization header.

    It is intended for endpoints where authentication is
    optional, such as public course/skill browsing.

    Invalid authentication tokens are still rejected rather
    than silently treated as anonymous requests.
    """

    if not token:
        return None

    return await _get_user_from_token(
        token=token,
        db=db,
    )


# ============================================================
# Current User + Roles
# ============================================================

async def get_current_user_with_roles(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> tuple[User, list[str]]:
    user = await _get_user_from_token(
        token=token,
        db=db,
    )

    result = await db.execute(
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

    roles = list(result.scalars().all())

    return user, roles