from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class NotificationPreferenceLevel(str, Enum):
    ALL = "ALL"
    IMPORTANT_ONLY = "IMPORTANT_ONLY"
    MUTED = "MUTED"


class UserNotificationPreference(Base):
    __tablename__ = "user_notification_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    notification_type: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
    )

    preference: Mapped[str] = mapped_column(
        String(30),
        default=NotificationPreferenceLevel.ALL.value,
        nullable=False,
    )

    enabled_email: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    enabled_sms: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    enabled_push: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user = relationship(
        "User",
        backref="notification_preferences",
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "notification_type",
            name="uq_user_notification_preference",
        ),
    )
