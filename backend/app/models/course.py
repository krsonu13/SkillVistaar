from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CourseDeliveryMode(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    HYBRID = "HYBRID"


class CourseLevel(str, Enum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"


class CourseStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    PUBLISHED = "PUBLISHED"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    institution_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "institution_profiles.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    course_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    short_description: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    course_level: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=CourseLevel.BEGINNER.value,
        server_default=CourseLevel.BEGINNER.value,
    )

    delivery_mode: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=CourseDeliveryMode.OFFLINE.value,
        server_default=CourseDeliveryMode.OFFLINE.value,
    )

    duration_value: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    duration_unit: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="MONTHS",
        server_default="MONTHS",
    )

    fee: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="INR",
        server_default="INR",
    )

    eligibility: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    seats: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    batch_start_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    batch_end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    admission_start_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    admission_end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    syllabus: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    placement_support: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    placement_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=CourseStatus.DRAFT.value,
        server_default=CourseStatus.DRAFT.value,
    )

    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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

    institution_profile = relationship(
        "InstitutionProfile",
        backref="courses",
    )

    __table_args__ = (
        UniqueConstraint(
            "institution_profile_id",
            "title",
            name="uq_course_institution_title",
        ),
        Index(
            "ix_courses_institution",
            "institution_profile_id",
        ),
        Index(
            "ix_courses_status",
            "status",
        ),
        Index(
            "ix_courses_delivery_mode",
            "delivery_mode",
        ),
        Index(
            "ix_courses_level",
            "course_level",
        ),
        Index(
            "ix_courses_admission_dates",
            "admission_start_date",
            "admission_end_date",
        ),
        Index(
            "ix_courses_batch_dates",
            "batch_start_date",
            "batch_end_date",
        ),
        Index(
            "ix_courses_featured",
            "is_featured",
        ),
    )