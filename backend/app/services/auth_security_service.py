from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.models.user import User


class AuthSecurityError(Exception):
    pass


class AccountLockedError(AuthSecurityError):
    pass


class InvalidCredentialsError(AuthSecurityError):
    pass


class AuthSecurityService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_identifier(
        self,
        identifier: str,
    ) -> User | None:
        identifier = identifier.strip().lower()

        result = await self.db.execute(
            select(User).where(
                (User.email == identifier)
                | (User.phone == identifier)
            )
        )

        return result.scalar_one_or_none()

    def is_locked(self, user: User) -> bool:
        if not user.locked_until:
            return False

        now = datetime.now(timezone.utc)

        locked_until = user.locked_until

        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(
                tzinfo=timezone.utc
            )

        return locked_until > now

    async def register_failed_login(
        self,
        user: User,
    ) -> None:
        user.failed_login_attempts += 1

        if (
            user.failed_login_attempts
            >= settings.MAX_LOGIN_ATTEMPTS
        ):
            user.locked_until = (
                datetime.now(timezone.utc)
                + timedelta(
                    minutes=settings.LOGIN_LOCKOUT_MINUTES
                )
            )

        await self.db.flush()

    async def reset_login_failures(
        self,
        user: User,
    ) -> None:
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.now(
            timezone.utc
        )

        await self.db.flush()

    async def authenticate(
        self,
        identifier: str,
        password: str,
    ) -> User:
        user = await self.get_user_by_identifier(
            identifier
        )

        if user is None:
            raise InvalidCredentialsError(
                "Invalid credentials."
            )

        if self.is_locked(user):
            raise AccountLockedError(
                "Account is temporarily locked. "
                "Please try again later."
            )

        if not user.is_active or user.is_suspended:
            raise InvalidCredentialsError(
                "Account is inactive or suspended."
            )

        if not verify_password(
            password,
            user.password_hash,
        ):
            await self.register_failed_login(user)

            raise InvalidCredentialsError(
                "Invalid credentials."
            )

        await self.reset_login_failures(user)

        return user

    async def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str,
    ) -> None:
        if not verify_password(
            current_password,
            user.password_hash,
        ):
            raise InvalidCredentialsError(
                "Current password is incorrect."
            )

        validate_password_strength(new_password)

        if verify_password(
            new_password,
            user.password_hash,
        ):
            raise AuthSecurityError(
                "New password must be different "
                "from the current password."
            )

        user.password_hash = hash_password(
            new_password
        )

        user.password_changed_at = datetime.now(
            timezone.utc
        )

        await self.db.flush()

    async def force_password_reset(
        self,
        user_id: UUID,
        new_password: str,
    ) -> None:
        validate_password_strength(new_password)

        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )

        user = result.scalar_one_or_none()

        if user is None:
            raise AuthSecurityError(
                "User not found."
            )

        user.password_hash = hash_password(
            new_password
        )

        user.password_changed_at = datetime.now(
            timezone.utc
        )

        await self.db.flush()