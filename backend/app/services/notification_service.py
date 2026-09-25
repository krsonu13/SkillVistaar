from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import (
    Notification,
    NotificationPriority,
    NotificationType,
)
from app.models.user import User
from app.models.user_notification_preference import (
    NotificationPreferenceLevel,
    UserNotificationPreference,
)
from app.schemas.notification import (
    NotificationPreferenceUpdate,
)


class NotificationServiceError(Exception):
    pass


class NotificationAccessDeniedError(NotificationServiceError):
    pass


class NotificationNotFoundError(NotificationServiceError):
    pass


class NotificationValidationError(NotificationServiceError):
    pass


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------------------------------------------------------------
    # USER SAFETY
    # ---------------------------------------------------------------

    @staticmethod
    def ensure_user_active(user: User) -> None:
        if not user.is_active or user.is_suspended:
            raise NotificationAccessDeniedError(
                "Your account is not active."
            )

    # ---------------------------------------------------------------
    # PREFERENCE
    # ---------------------------------------------------------------

    async def get_preference(
        self,
        user_id: UUID,
        notification_type: str,
    ) -> UserNotificationPreference | None:
        result = await self.db.execute(
            select(UserNotificationPreference).where(
                UserNotificationPreference.user_id == user_id,
                UserNotificationPreference.notification_type
                == notification_type,
            )
        )

        return result.scalar_one_or_none()

    async def should_create_notification(
        self,
        user_id: UUID,
        notification_type: str,
        priority: str,
    ) -> bool:
        preference = await self.get_preference(
            user_id,
            notification_type,
        )

        if preference is None:
            return True

        if (
            preference.preference
            == NotificationPreferenceLevel.MUTED.value
        ):
            return False

        if (
            preference.preference
            == NotificationPreferenceLevel.IMPORTANT_ONLY.value
        ):
            return priority in {
                NotificationPriority.HIGH.value,
                NotificationPriority.CRITICAL.value,
            }

        return True

    async def update_preference(
        self,
        user: User,
        notification_type: str,
        data: NotificationPreferenceUpdate,
    ) -> UserNotificationPreference:
        self.ensure_user_active(user)

        valid_types = {
            item.value
            for item in NotificationType
        }

        if notification_type not in valid_types:
            raise NotificationValidationError(
                "Invalid notification type."
            )

        preference = await self.get_preference(
            user.id,
            notification_type,
        )

        if preference is None:
            preference = UserNotificationPreference(
                user_id=user.id,
                notification_type=notification_type,
            )
            self.db.add(preference)

        preference.preference = data.preference
        preference.enabled_email = data.enabled_email
        preference.enabled_sms = data.enabled_sms
        preference.enabled_push = data.enabled_push

        await self.db.commit()
        await self.db.refresh(preference)

        return preference

    async def get_preferences(
        self,
        user: User,
    ) -> list[UserNotificationPreference]:
        self.ensure_user_active(user)

        result = await self.db.execute(
            select(UserNotificationPreference)
            .where(
                UserNotificationPreference.user_id == user.id
            )
            .order_by(
                UserNotificationPreference.notification_type.asc()
            )
        )

        return list(result.scalars().all())

    # ---------------------------------------------------------------
    # CREATE
    # ---------------------------------------------------------------

    async def create_notification(
        self,
        user_id: UUID,
        notification_type: str,
        title: str,
        message: str,
        *,
        priority: str = NotificationPriority.NORMAL,
        title_mr: str | None = None,
        message_mr: str | None = None,
        translation_key: str | None = None,
        translation_params: dict | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        action_url: str | None = None,
    ) -> Notification | None:
        valid_types = {
            getattr(NotificationType, k)
            for k in dir(NotificationType)
            if not k.startswith("_") and isinstance(getattr(NotificationType, k), str)
        }

        if notification_type not in valid_types:
            raise NotificationValidationError(
                "Invalid notification type."
            )

        valid_priorities = {
            getattr(NotificationPriority, k)
            for k in dir(NotificationPriority)
            if not k.startswith("_") and isinstance(getattr(NotificationPriority, k), str)
        }

        if priority not in valid_priorities:
            raise NotificationValidationError(
                "Invalid notification priority."
            )

        if not await self.should_create_notification(
            user_id=user_id,
            notification_type=notification_type,
            priority=priority,
        ):
            return None

        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            priority=priority,
            title=title,
            message=message,
            title_mr=title_mr,
            message_mr=message_mr,
            translation_key=translation_key,
            translation_params=translation_params,
            entity_type=entity_type,
            entity_id=entity_id,
            action_url=action_url,
        )

        self.db.add(notification)

        await self.db.commit()
        await self.db.refresh(notification)

        return notification

    # ---------------------------------------------------------------
    # LIST
    # ---------------------------------------------------------------

    async def get_notifications(
        self,
        user: User,
        *,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False,
    ) -> tuple[list[Notification], int, int]:
        self.ensure_user_active(user)

        limit = min(max(limit, 1), 100)
        offset = max(offset, 0)

        conditions = [
            Notification.user_id == user.id,
        ]

        if unread_only:
            conditions.append(
                Notification.is_read.is_(False)
            )

        result = await self.db.execute(
            select(Notification)
            .where(*conditions)
            .order_by(
                Notification.created_at.desc()
            )
            .offset(offset)
            .limit(limit)
        )

        items = list(result.scalars().all())

        total_result = await self.db.execute(
            select(func.count(Notification.id))
            .where(*conditions)
        )

        total = int(total_result.scalar_one())

        unread_result = await self.db.execute(
            select(func.count(Notification.id))
            .where(
                Notification.user_id == user.id,
                Notification.is_read.is_(False),
            )
        )

        unread_count = int(
            unread_result.scalar_one()
        )

        return items, total, unread_count

    # ---------------------------------------------------------------
    # READ
    # ---------------------------------------------------------------

    async def get_user_notification(
        self,
        user: User,
        notification_id: UUID,
    ) -> Notification:
        self.ensure_user_active(user)

        result = await self.db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user.id,
            )
        )

        notification = result.scalar_one_or_none()

        if notification is None:
            raise NotificationNotFoundError(
                "Notification not found."
            )

        return notification

    async def mark_as_read(
        self,
        user: User,
        notification_id: UUID,
    ) -> Notification:
        notification = await self.get_user_notification(
            user,
            notification_id,
        )

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)

            await self.db.commit()
            await self.db.refresh(notification)

        return notification

    async def mark_all_as_read(
        self,
        user: User,
    ) -> int:
        self.ensure_user_active(user)

        result = await self.db.execute(
            select(Notification).where(
                Notification.user_id == user.id,
                Notification.is_read.is_(False),
            )
        )

        notifications = list(
            result.scalars().all()
        )

        now = datetime.now(timezone.utc)

        for notification in notifications:
            notification.is_read = True
            notification.read_at = now

        if notifications:
            await self.db.commit()

        return len(notifications)
