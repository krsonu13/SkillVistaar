from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class VerifierAuthorization(Base):
    """
    Defines which user is authorized to verify which type of application
    within which government jurisdiction.

    This is separate from the user's role because having a verifier role
    does not automatically grant unlimited verification authority.
    """

    __tablename__ = "verifier_authorizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    verifier_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    government_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("government_units.id", ondelete="CASCADE"),
        nullable=True,
    )

    application_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    granted_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    verifier = relationship(
        "User",
        foreign_keys=[verifier_user_id],
    )

    granted_by = relationship(
        "User",
        foreign_keys=[granted_by_user_id],
    )

    government_unit = relationship(
        "GovernmentUnit",
    )

    __table_args__ = (
        Index(
            "ix_verifier_authorizations_verifier_active",
            "verifier_user_id",
            "is_active",
        ),
        Index(
            "ix_verifier_authorizations_government_unit",
            "government_unit_id",
            "is_active",
        ),
        Index(
            "ix_verifier_authorizations_type",
            "application_type",
            "is_active",
        ),
    )