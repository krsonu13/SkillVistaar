from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, Index, Integer, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LabourMarketSnapshot(Base):
    __tablename__ = "labour_market_snapshots"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    government_unit_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("government_units.id", ondelete="RESTRICT"),
        nullable=True,
    )

    source_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("labour_market_sources.id", ondelete="SET NULL"),
        nullable=True,
    )

    skill_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="SET NULL"),
        nullable=True,
    )

    occupation_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    occupation_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    sector: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    employment_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    workplace_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    experience_min_years: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    experience_max_years: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    demand_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    supply_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
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

    notes: Mapped[str | None] = mapped_column(
        Text,
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

    government_unit = relationship("GovernmentUnit")
    source = relationship("LabourMarketSource")
    skill = relationship("Skill")

    __table_args__ = (
        Index(
            "ix_labour_snapshots_unit_period",
            "government_unit_id",
            "period_start",
            "period_end",
        ),
        Index(
            "ix_labour_snapshots_occupation",
            "occupation_name",
        ),
        Index(
            "ix_labour_snapshots_skill",
            "skill_id",
        ),
        Index(
            "ix_labour_snapshots_sector",
            "sector",
        ),
    )