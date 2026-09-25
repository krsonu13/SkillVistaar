from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    Date,
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


class CandidateProfileStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INCOMPLETE = "INCOMPLETE"
    SUSPENDED = "SUSPENDED"


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    government_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("government_units.id", ondelete="RESTRICT"),
        nullable=True,
    )

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    middle_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    last_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    date_of_birth: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    gender: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    headline: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    bio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    current_occupation: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    years_of_experience: Mapped[float] = mapped_column(
    default=0,
    server_default="0",
    nullable=False,
)

    highest_qualification: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    preferred_location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    preferred_job_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    preferred_workplace_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    profile_photo_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    cover_photo_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    resume_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    education: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
    )

    experience: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
    )

    projects: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
    )

    certifications: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
    )

    courses_completed: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
    )

    achievements: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
    )

    languages: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
    )

    career_preferences: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
    )

    profile_completion_percentage: Mapped[int] = mapped_column(
    default=0,
    server_default="0",
    nullable=False,
)

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=CandidateProfileStatus.INCOMPLETE.value,
        server_default=CandidateProfileStatus.INCOMPLETE.value,
    )

    is_public: Mapped[bool] = mapped_column(
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

    user = relationship(
        "User",
        foreign_keys=[user_id],
    )

    government_unit = relationship(
        "GovernmentUnit",
        foreign_keys=[government_unit_id],
    )

    __table_args__ = (
        Index(
            "ix_candidate_profiles_government_unit",
            "government_unit_id",
        ),
        Index(
            "ix_candidate_profiles_status",
            "status",
        ),
        Index(
            "ix_candidate_profiles_public",
            "is_public",
        ),
        Index(
            "ix_candidate_profiles_occupation",
            "current_occupation",
        ),
    )