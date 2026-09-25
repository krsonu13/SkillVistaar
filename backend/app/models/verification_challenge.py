from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class VerificationChallenge(Base):
    __tablename__ = "verification_challenges"

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

    # EMAIL or PHONE
    channel: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    # SIGNUP, LOGIN, PASSWORD_RESET, etc.
    purpose: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # Hash of the OTP. The actual OTP is never stored.
    code_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    max_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
    )

    consumed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user = relationship(
        "User",
        back_populates="verification_challenges",
    )

    __table_args__ = (
        Index(
            "ix_verification_challenges_user_channel_purpose",
            "user_id",
            "channel",
            "purpose",
        ),
        Index(
            "ix_verification_challenges_expiry",
            "expires_at",
        ),
        Index(
            "ix_verification_challenges_active",
            "user_id",
            "consumed",
            "expires_at",
        ),
    )