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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class OrganizationMemberRole(str, Enum):
    ORG_ADMIN = "ORG_ADMIN"
    HR = "HR"
    JOB_POSTER = "JOB_POSTER"
    ASSESSMENT_MANAGER = "ASSESSMENT_MANAGER"
    INSTITUTION_ADMIN = "INSTITUTION_ADMIN"


class OrganizationMember(Base):
    __tablename__ = "organization_members"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    role_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    invited_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    joined_at: Mapped[datetime | None] = mapped_column(
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

    organization = relationship(
        "Organization",
        backref="members",
    )

    user = relationship(
        "User",
        foreign_keys=[user_id],
    )

    invited_by = relationship(
        "User",
        foreign_keys=[invited_by_user_id],
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "user_id",
            "role_code",
            name="uq_organization_member_role",
        ),
        Index(
            "ix_organization_members_org_active",
            "organization_id",
            "is_active",
        ),
        Index(
            "ix_organization_members_user_active",
            "user_id",
            "is_active",
        ),
        Index(
            "ix_organization_members_role_active",
            "role_code",
            "is_active",
        ),
    )