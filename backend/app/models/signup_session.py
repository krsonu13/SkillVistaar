from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SignupVerificationSession(Base):
    __tablename__ = "signup_verification_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    session_token: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    account_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # Primary Contact (EMAIL or PHONE)
    primary_channel: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    primary_identifier: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # SHA-256 hash of primary OTP - raw OTP is never stored
    primary_code_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    primary_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    primary_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Secondary Contact (the other of PHONE or EMAIL)
    secondary_channel: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    secondary_identifier: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # SHA-256 hash of secondary OTP - raw OTP is never stored
    secondary_code_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    secondary_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    secondary_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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

    completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index(
            "ix_signup_sessions_token_completed",
            "session_token",
            "completed",
        ),
        Index(
            "ix_signup_sessions_expires_at",
            "expires_at",
        ),
    )
