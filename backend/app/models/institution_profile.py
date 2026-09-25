from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class InstitutionVerificationStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    MORE_INFORMATION_REQUIRED = "MORE_INFORMATION_REQUIRED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


class InstitutionProfile(Base):
    __tablename__ = "institution_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    institution_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
    )

    accreditation_body: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    accreditation_number: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    institution_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    affiliation: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    ownership_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    established_year: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    trainers: Mapped[dict | list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    infrastructure: Mapped[dict | list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    partnerships: Mapped[dict | list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    curriculum_alignment: Mapped[dict | list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    website: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    state: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    country: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="India",
        server_default="India",
    )

    verification_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=InstitutionVerificationStatus.PENDING.value,
        server_default=InstitutionVerificationStatus.PENDING.value,
    )

    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    suspended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
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

    organization = relationship(
        "Organization",
        foreign_keys=[organization_id],
    )

    __table_args__ = (
        Index(
            "ix_institution_profiles_status",
            "verification_status",
        ),
        Index(
            "ix_institution_profiles_city_state",
            "city",
            "state",
        ),
        Index(
            "ix_institution_profiles_active",
            "is_active",
        ),
    )