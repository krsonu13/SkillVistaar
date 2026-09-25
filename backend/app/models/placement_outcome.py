from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, Index, Integer, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PlacementOutcome(Base):
    __tablename__ = "placement_outcomes"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    institution_profile_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("institution_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )

    course_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="SET NULL"),
        nullable=True,
    )

    government_unit_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("government_units.id", ondelete="RESTRICT"),
        nullable=True,
    )

    occupation_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    sector: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    total_learners: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    placed_learners: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    employment_rate: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    average_salary: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    median_salary: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    currency: Mapped[str] = mapped_column(
        String(10),
        default="INR",
        nullable=False,
    )

    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    source_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("labour_market_sources.id", ondelete="SET NULL"),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        String(2000),
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

    institution_profile = relationship("InstitutionProfile")
    course = relationship("Course")
    government_unit = relationship("GovernmentUnit")
    source = relationship("LabourMarketSource")

    __table_args__ = (
        Index(
            "ix_placement_outcomes_institution",
            "institution_profile_id",
        ),
        Index(
            "ix_placement_outcomes_course",
            "course_id",
        ),
        Index(
            "ix_placement_outcomes_unit_period",
            "government_unit_id",
            "period_start",
            "period_end",
        ),
        Index(
            "ix_placement_outcomes_occupation",
            "occupation_name",
        ),
    )