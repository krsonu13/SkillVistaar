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
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AssessmentType(str, Enum):
    MCQ = "MCQ"
    APTITUDE = "APTITUDE"
    TECHNICAL = "TECHNICAL"
    SUBJECTIVE = "SUBJECTIVE"
    PROGRAMMING = "PROGRAMMING"


class AssessmentStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "organizations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    assessment_type: Mapped[str] = mapped_column(
        String(40),
        default=AssessmentType.MCQ.value,
        nullable=False,
    )

    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        default=30,
        nullable=False,
    )

    total_marks: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    passing_percentage: Mapped[float] = mapped_column(
        default=40.0,
        nullable=False,
    )

    max_attempts: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    randomize_questions: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    show_result_immediately: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    instructions: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(40),
        default=AssessmentStatus.DRAFT.value,
        nullable=False,
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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

    organization = relationship(
        "Organization",
        backref="assessments",
    )

    created_by_user = relationship(
        "User",
        backref="created_assessments",
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "title",
            name="uq_assessment_organization_title",
        ),
        Index(
            "ix_assessments_organization_status",
            "organization_id",
            "status",
        ),
        Index(
            "ix_assessments_type_status",
            "assessment_type",
            "status",
        ),
        Index(
            "ix_assessments_published_at",
            "published_at",
        ),
    )