from __future__ import annotations

import uuid
from enum import Enum

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AssessmentQuestionType(str, Enum):
    MCQ = "MCQ"
    MULTIPLE_SELECT = "MULTIPLE_SELECT"
    TRUE_FALSE = "TRUE_FALSE"
    SHORT_ANSWER = "SHORT_ANSWER"


class AssessmentQuestionDifficulty(str, Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class AssessmentQuestion(Base):
    __tablename__ = "assessment_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "assessments.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    question_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    question_type: Mapped[str] = mapped_column(
        String(40),
        default=AssessmentQuestionType.MCQ.value,
        nullable=False,
    )

    difficulty: Mapped[str] = mapped_column(
        String(20),
        default=AssessmentQuestionDifficulty.MEDIUM.value,
        nullable=False,
    )

    options: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    correct_answer: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    explanation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    marks: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    negative_marks: Mapped[float] = mapped_column(
        default=0.0,
        nullable=False,
    )

    skill_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "skills.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    sequence_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    assessment = relationship(
        "Assessment",
        backref="questions",
    )

    skill = relationship(
        "Skill",
        backref="assessment_questions",
    )

    __table_args__ = (
        UniqueConstraint(
            "assessment_id",
            "sequence_number",
            name="uq_assessment_question_sequence",
        ),
        Index(
            "ix_assessment_questions_assessment_active",
            "assessment_id",
            "is_active",
        ),
        Index(
            "ix_assessment_questions_skill",
            "skill_id",
        ),
        Index(
            "ix_assessment_questions_type_difficulty",
            "question_type",
            "difficulty",
        ),
    )