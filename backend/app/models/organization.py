from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class OrganizationType(str, Enum):
    EMPLOYER = "EMPLOYER"
    TRAINING_INSTITUTE = "TRAINING_INSTITUTE"


class OrganizationVerificationStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    MORE_INFORMATION_REQUIRED = "MORE_INFORMATION_REQUIRED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # User who originally created/owns the organization.
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    government_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("government_units.id", ondelete="RESTRICT"),
        nullable=True,
    )

    organization_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    legal_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    display_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    registration_number: Mapped[str | None] = mapped_column(
        String(150),
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

    website: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    logo_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    cover_photo_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    sector: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    company_size: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    branches: Mapped[dict | list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    contact_persons: Mapped[dict | list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    industry_skills: Mapped[dict | list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    verification_status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=OrganizationVerificationStatus.PENDING.value,
        server_default=OrganizationVerificationStatus.PENDING.value,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
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

    owner = relationship(
        "User",
        foreign_keys=[owner_user_id],
    )

    government_unit = relationship(
        "GovernmentUnit",
    )

    __table_args__ = (
        Index(
            "ix_organizations_owner",
            "owner_user_id",
        ),
        Index(
            "ix_organizations_type_status",
            "organization_type",
            "verification_status",
        ),
        Index(
            "ix_organizations_government_unit",
            "government_unit_id",
            "is_active",
        ),
        Index(
            "ix_organizations_registration",
            "registration_number",
        ),
    )