from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class JobStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    PUBLISHED = "PUBLISHED"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


class WorkMode(str, Enum):
    ONSITE = "ONSITE"
    HYBRID = "HYBRID"
    REMOTE = "REMOTE"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Existing database field — preserve it.
    posted_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # New explicit creator field.
    # Nullable for backward compatibility with existing rows.
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role_family: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    occupation_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    responsibilities: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Preserve existing field.
    qualifications: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # New normalized alias for future API use.
    qualification: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Preserve existing experience fields.
    min_experience_years: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    max_experience_years: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # New aliases for the expanded workflow.
    minimum_experience: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    maximum_experience: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # Existing location fields.
    city: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    district: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    state: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Preserve existing employment field.
    employment_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Preserve existing workplace field.
    workplace_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # New standardized work mode.
    work_mode: Mapped[str] = mapped_column(
        String(30),
        default=WorkMode.ONSITE.value,
        nullable=False,
    )

    # Preserve existing salary fields.
    min_salary: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    max_salary: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    salary_currency: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    # New aliases.
    salary_min: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    salary_max: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    vacancies: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    shift: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    travel_required: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    joining_timeline: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    # Existing database uses DATE.
    application_deadline: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default=JobStatus.DRAFT.value,
        nullable=False,
    )

    is_public: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Preserve existing field.
    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Explicit relationships.
    organization = relationship(
        "Organization",
        foreign_keys=[organization_id],
    )

    posted_by = relationship(
        "User",
        foreign_keys=[posted_by_user_id],
    )

    created_by = relationship(
        "User",
        foreign_keys=[created_by_user_id],
    )

    skill_requirements = relationship(
        "JobSkillRequirement",
        back_populates="job",
        cascade="all, delete-orphan",
    )

    screening_questions = relationship(
        "JobScreeningQuestion",
        back_populates="job",
        cascade="all, delete-orphan",
    )

    applications = relationship(
        "JobApplication",
        back_populates="job",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_jobs_organization_status", "organization_id", "status"),
        Index("ix_jobs_posted_by", "posted_by_user_id"),
        Index("ix_jobs_employment_workplace", "employment_type", "workplace_type"),
        Index("ix_jobs_status_deadline", "status", "application_deadline"),
        Index("ix_jobs_location", "city", "state"),
        Index("ix_jobs_organization_id", "organization_id"),
        Index("ix_jobs_status", "status"),
        Index("ix_jobs_role_family", "role_family"),
        Index("ix_jobs_district", "district"),
        Index("ix_jobs_state", "state"),
        Index("ix_jobs_created_at", "created_at"),
    )