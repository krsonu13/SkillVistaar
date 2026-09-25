from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Role(Base):
    """
    Authorization role used by SkillVistaar.

    Roles define what a user is allowed to do. They are intentionally
    separate from account types such as Government, Employer,
    Training Institute, and Candidate.

    Examples:
        SUPER_ADMIN
        GOVERNMENT_ADMIN
        GOVERNMENT_VERIFIER
        ORG_ADMIN
        HR
        JOB_POSTER
        ASSESSMENT_MANAGER
        INSTITUTION_ADMIN
        CANDIDATE
    """

    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_system_role: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
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

    user_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole",
        back_populates="role",
    )

    __table_args__ = (
        Index(
            "ix_roles_active",
            "is_active",
        ),
        Index(
            "ix_roles_system_active",
            "is_system_role",
            "is_active",
        ),
    )
