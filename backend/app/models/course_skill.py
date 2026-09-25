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
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CourseSkillImportance(str, Enum):
    CORE = "CORE"
    IMPORTANT = "IMPORTANT"
    OPTIONAL = "OPTIONAL"


class CourseSkill(Base):
    __tablename__ = "course_skills"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "courses.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "skills.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    importance: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=CourseSkillImportance.CORE.value,
        server_default=CourseSkillImportance.CORE.value,
    )

    proficiency_level: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="BEGINNER",
        server_default="BEGINNER",
    )

    is_mandatory: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    module_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        String(1000),
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

    course = relationship(
        "Course",
        backref="skill_mappings",
    )

    skill = relationship(
        "Skill",
        backref="course_mappings",
    )

    __table_args__ = (
        UniqueConstraint(
            "course_id",
            "skill_id",
            name="uq_course_skill",
        ),
        Index(
            "ix_course_skills_course",
            "course_id",
        ),
        Index(
            "ix_course_skills_skill",
            "skill_id",
        ),
        Index(
            "ix_course_skills_importance",
            "importance",
        ),
        Index(
            "ix_course_skills_proficiency",
            "proficiency_level",
        ),
    )