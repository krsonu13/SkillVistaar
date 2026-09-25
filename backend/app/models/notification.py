from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class NotificationType:
    JOB_MATCH = "JOB_MATCH"
    NEW_JOB = "NEW_JOB"
    NEW_COURSE = "NEW_COURSE"
    ADMISSION_OPEN = "ADMISSION_OPEN"
    CERTIFICATE_VERIFIED = "CERTIFICATE_VERIFIED"
    CERTIFICATE_REJECTED = "CERTIFICATE_REJECTED"
    ASSESSMENT_INVITATION = "ASSESSMENT_INVITATION"
    ASSESSMENT_RESULT = "ASSESSMENT_RESULT"
    GOVERNMENT_ALERT = "GOVERNMENT_ALERT"
    MARKET_TREND = "MARKET_TREND"
    FOLLOWED_ORGANIZATION_UPDATE = "FOLLOWED_ORGANIZATION_UPDATE"
    FOLLOW_RECEIVED = "FOLLOW_RECEIVED"
    VERIFICATION_STATUS_UPDATED = "VERIFICATION_STATUS_UPDATED"
    MESSAGE_RECEIVED = "MESSAGE_RECEIVED"
    MESSAGE_REQUEST = "MESSAGE_REQUEST"


class NotificationPriority:
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Notification(Base):
    __tablename__ = "notifications"

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

    priority: Mapped[str] = mapped_column(
    String(20),
    default=NotificationPriority.NORMAL,
    server_default="NORMAL",
    nullable=False,
)

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    title_mr: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    message_mr: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    translation_key: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    translation_params: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    entity_type: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    action_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Legacy compatibility fields.
    #
    # These columns already exist in the database and are intentionally
    # retained. They are not part of the new notification API, but keeping
    # them mapped prevents Alembic from attempting to remove them.
    # ------------------------------------------------------------------

    channel: Mapped[str] = mapped_column(
        String(30),
        default="IN_APP",
        nullable=False,
    )

    reference_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    reference_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
    )

    user = relationship(
        "User",
        backref="notifications",
    )

    __table_args__ = (
        Index(
            "ix_notifications_user_created",
            "user_id",
            "created_at",
        ),
        Index(
            "ix_notifications_user_unread",
            "user_id",
            "is_read",
        ),
        Index(
            "ix_notifications_type",
            "notification_type",
        ),
        Index(
            "ix_notifications_entity",
            "entity_type",
            "entity_id",
        ),

        # Legacy indexes intentionally retained for DB compatibility.
        Index(
            "ix_notifications_user_id",
            "user_id",
        ),
        Index(
            "ix_notifications_user_read",
            "user_id",
            "is_read",
        ),
    )