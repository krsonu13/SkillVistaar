import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AssessmentAttemptStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    AUTO_SUBMITTED = "AUTO_SUBMITTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class AssessmentAttempt(Base):
    __tablename__ = "assessment_attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    invitation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "assessment_invitations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "assessments.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "candidate_profiles.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    attempt_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default=AssessmentAttemptStatus.NOT_STARTED.value,
        nullable=False,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    total_questions: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    answered_questions: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    correct_answers: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    wrong_answers: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    unanswered_questions: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    total_marks: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    obtained_marks: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    percentage: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    passed: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
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

    invitation = relationship(
        "AssessmentInvitation",
        backref="attempts",
    )

    assessment = relationship(
        "Assessment",
        backref="attempts",
    )

    candidate_profile = relationship(
        "CandidateProfile",
        backref="assessment_attempts",
    )

    __table_args__ = (
        UniqueConstraint(
            "invitation_id",
            "attempt_number",
            name="uq_assessment_attempt_invitation_number",
        ),
        Index(
            "ix_assessment_attempts_invitation_status",
            "invitation_id",
            "status",
        ),
        Index(
            "ix_assessment_attempts_candidate_status",
            "candidate_profile_id",
            "status",
        ),
        Index(
            "ix_assessment_attempts_assessment_status",
            "assessment_id",
            "status",
        ),
        Index(
            "ix_assessment_attempts_submitted_at",
            "submitted_at",
        ),
    )