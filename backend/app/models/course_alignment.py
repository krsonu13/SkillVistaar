from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, Index, String, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CourseAlignment(Base):
    __tablename__ = "course_alignments"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    course_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
    )

    skill_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="RESTRICT"),
        nullable=False,
    )

    government_unit_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("government_units.id", ondelete="RESTRICT"),
        nullable=True,
    )

    demand_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    skill_coverage_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    alignment_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    alignment_status: Mapped[str] = mapped_column(
        String(40),
        default="PARTIALLY_ALIGNED",
        nullable=False,
    )

    recommended_action: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
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

    course = relationship("Course")
    skill = relationship("Skill")
    government_unit = relationship("GovernmentUnit")

    __table_args__ = (
        UniqueConstraint(
            "course_id",
            "skill_id",
            "government_unit_id",
            name="uq_course_alignment_course_skill_unit",
        ),
        Index(
            "ix_course_alignments_course",
            "course_id",
        ),
        Index(
            "ix_course_alignments_skill",
            "skill_id",
        ),
        Index(
            "ix_course_alignments_status",
            "alignment_status",
        ),
        Index(
            "ix_course_alignments_unit",
            "government_unit_id",
        ),
    )