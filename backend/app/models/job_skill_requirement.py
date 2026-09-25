from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from enum import Enum

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SkillRequirementType(str, Enum):
    REQUIRED = "REQUIRED"
    PREFERRED = "PREFERRED"
    OPTIONAL = "OPTIONAL"


class SkillProficiencyLevel(str, Enum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"
    EXPERT = "EXPERT"


class JobSkillRequirement(Base):
    __tablename__ = "job_skill_requirements"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    job_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "jobs.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    skill_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "skills.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    proficiency_level: Mapped[str] = mapped_column(
        String(30),
        default="INTERMEDIATE",
        nullable=False,
    )

    is_required: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    minimum_years: Mapped[float] = mapped_column(
        default=0.0,
        nullable=False,
    )

    @property
    def requirement_type(self) -> str:
        return SkillRequirementType.REQUIRED.value if self.is_required else SkillRequirementType.PREFERRED.value

    @property
    def is_mandatory(self) -> bool:
        return self.is_required

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    job = relationship(
        "Job",
        back_populates="skill_requirements",
    )

    skill = relationship(
        "Skill",
    )

    __table_args__ = (
        UniqueConstraint(
            "job_id",
            "skill_id",
            name="uq_job_skill_requirement",
        ),
        Index(
            "ix_job_skill_requirements_job_id",
            "job_id",
        ),
        Index(
            "ix_job_skill_requirements_skill_id",
            "skill_id",
        ),
    )