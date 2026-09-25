from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ScreeningQuestionType(str, Enum):
    SINGLE_CHOICE = "SINGLE_CHOICE"
    YES_NO = "YES_NO"
    NUMBER = "NUMBER"
    TEXT = "TEXT"


class JobScreeningQuestion(Base):
    __tablename__ = "job_screening_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "jobs.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    question: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    question_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    options: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    is_required: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    display_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    job = relationship(
        "Job",
        back_populates="screening_questions",
    )

    __table_args__ = (
        Index(
            "ix_job_screening_questions_job_id",
            "job_id",
        ),
        Index(
            "ix_job_screening_questions_job_order",
            "job_id",
            "display_order",
        ),
    )
