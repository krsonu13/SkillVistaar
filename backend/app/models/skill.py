from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class SkillType(str, Enum):
    TECHNICAL = "TECHNICAL"
    SOFT = "SOFT"
    DOMAIN = "DOMAIN"
    TOOLS = "TOOLS"
    LANGUAGE = "LANGUAGE"
    DIGITAL = "DIGITAL"
    OTHER = "OTHER"


class SkillStatus(str, Enum):
    ACTIVE = "ACTIVE"
    EMERGING = "EMERGING"
    LOW_DEMAND = "LOW_DEMAND"
    OBSOLETE = "OBSOLETE"
    ARCHIVED = "ARCHIVED"


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )

    normalized_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )

    skill_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    category: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=SkillStatus.ACTIVE.value,
        server_default=SkillStatus.ACTIVE.value,
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
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

    __table_args__ = (
        Index(
            "ix_skills_type_status",
            "skill_type",
            "status",
        ),
        Index(
            "ix_skills_category_active",
            "category",
            "is_active",
        ),
        Index(
            "ix_skills_normalized_name",
            "normalized_name",
        ),
    )