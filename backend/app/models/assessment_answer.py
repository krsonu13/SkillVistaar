import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AssessmentAnswer(Base):
    __tablename__ = "assessment_answers"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    attempt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "assessment_attempts.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "assessment_questions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    # Candidate's submitted answer.
    # Stored as text so MCQ, multiple-select, true/false,
    # and short-answer responses can all be supported.
    answer_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # These fields are populated by the scoring service.
    is_answered: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
    )

    is_correct: Mapped[bool | None] = mapped_column(
        default=None,
        nullable=True,
    )

    marks_awarded: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    answered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    evaluated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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

    attempt = relationship(
        "AssessmentAttempt",
        backref="answers",
    )

    question = relationship(
        "AssessmentQuestion",
        backref="answers",
    )

    __table_args__ = (
        UniqueConstraint(
            "attempt_id",
            "question_id",
            name="uq_assessment_answer_attempt_question",
        ),
        Index(
            "ix_assessment_answers_attempt",
            "attempt_id",
        ),
        Index(
            "ix_assessment_answers_question",
            "question_id",
        ),
        Index(
            "ix_assessment_answers_attempt_correct",
            "attempt_id",
            "is_correct",
        ),
    )