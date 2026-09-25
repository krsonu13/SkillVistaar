from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.application_status_history import ApplicationStatusHistory


class ApplicationStatus(str, Enum):
    APPLIED = "APPLIED"
    UNDER_REVIEW = "UNDER_REVIEW"
    SHORTLISTED = "SHORTLISTED"
    ASSESSMENT = "ASSESSMENT"
    INTERVIEW = "INTERVIEW"
    SELECTED = "SELECTED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


class JobApplication(Base):
    __tablename__ = "job_applications"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    job_id: Mapped[UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )

    candidate_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )

    candidate_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(40),
        default=ApplicationStatus.APPLIED.value,
        nullable=False,
    )

    cover_letter: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    resume_document_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("private_documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    match_score: Mapped[float] = mapped_column(
        default=0.0,
        nullable=False,
    )

    matched_required_skills: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    total_required_skills: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    matched_preferred_skills: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    total_preferred_skills: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    consent_to_share_profile: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    applied_at: Mapped[datetime] = mapped_column(
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

    job = relationship(
        "Job",
        back_populates="applications",
    )

    status_history = relationship(
        ApplicationStatusHistory,
        back_populates="application",
        cascade="all, delete-orphan",
    )

    candidate_profile = relationship(
        "CandidateProfile",
        backref="job_applications",
    )

    __table_args__ = (
        UniqueConstraint(
            "job_id",
            "candidate_profile_id",
            name="uq_job_candidate_application",
        ),
        Index(
            "ix_job_applications_job_id",
            "job_id",
        ),
        Index(
            "ix_job_applications_candidate_profile_id",
            "candidate_profile_id",
        ),
        Index(
            "ix_job_applications_status",
            "status",
        ),
        Index(
            "ix_job_applications_match_score",
            "match_score",
        ),
    )
