from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FollowTargetType(str, Enum):
    USER = "USER"
    ORGANIZATION = "ORGANIZATION"
    INSTITUTION = "INSTITUTION"
    GOVERNMENT_DEPARTMENT = "GOVERNMENT_DEPARTMENT"
    SECTOR = "SECTOR"
    OCCUPATION = "OCCUPATION"


class FollowNotificationPreference(str, Enum):
    ALL = "ALL"
    IMPORTANT_ONLY = "IMPORTANT_ONLY"
    MUTED = "MUTED"


class Following(Base):
    __tablename__ = "followings"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    target_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    target_id: Mapped[UUID | None] = mapped_column(
        nullable=True,
    )

    target_key: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    notification_preference: Mapped[str] = mapped_column(
        String(30),
        default=FollowNotificationPreference.ALL.value,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user = relationship(
        "User",
        backref="followings",
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "target_type",
            "target_id",
            "target_key",
            name="uq_following_target",
        ),
        Index("ix_followings_user_id", "user_id"),
        Index("ix_followings_target", "target_type", "target_id"),
        Index("ix_followings_active", "user_id", "is_active"),
        Index(
            "uq_followings_user_target_id",
            "user_id",
            "target_type",
            "target_id",
            unique=True,
            postgresql_where=text("target_id IS NOT NULL"),
        ),
        Index(
            "uq_followings_user_target_key",
            "user_id",
            "target_type",
            "target_key",
            unique=True,
            postgresql_where=text("target_key IS NOT NULL"),
        ),
    )