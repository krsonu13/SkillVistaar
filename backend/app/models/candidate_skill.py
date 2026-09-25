from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class CandidateSkillStatus(str, Enum):
    SELF_DECLARED = "SELF_DECLARED"
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class CandidateSkillProficiency(str, Enum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"
    EXPERT = "EXPERT"


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )

    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="RESTRICT"),
        nullable=False,
    )

    proficiency_level: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=CandidateSkillProficiency.BEGINNER.value,
        server_default=CandidateSkillProficiency.BEGINNER.value,
    )

    years_of_experience: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0,
        server_default="0",
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=CandidateSkillStatus.SELF_DECLARED.value,
        server_default=CandidateSkillStatus.SELF_DECLARED.value,
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    verified_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    verification_notes: Mapped[str | None] = mapped_column(
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

    candidate_profile = relationship(
        "CandidateProfile",
        foreign_keys=[candidate_profile_id],
    )

    skill = relationship(
        "Skill",
        foreign_keys=[skill_id],
    )

    verified_by = relationship(
        "User",
        foreign_keys=[verified_by_user_id],
    )

    __table_args__ = (
        UniqueConstraint(
            "candidate_profile_id",
            "skill_id",
            name="uq_candidate_skill_profile_skill",
        ),
        Index(
            "ix_candidate_skills_candidate_profile",
            "candidate_profile_id",
        ),
        Index(
            "ix_candidate_skills_skill",
            "skill_id",
        ),
        Index(
            "ix_candidate_skills_status",
            "status",
        ),
        Index(
            "ix_candidate_skills_proficiency",
            "proficiency_level",
        ),
        Index(
            "ix_candidate_skills_verified",
            "status",
            "verified_at",
        ),
    )