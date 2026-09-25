from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, Index, Integer, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class EmergingSkillTrend(Base):
    __tablename__ = "emerging_skill_trends"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
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

    source_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("labour_market_sources.id", ondelete="SET NULL"),
        nullable=True,
    )

    demand_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    growth_rate: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    trend_direction: Mapped[str] = mapped_column(
        String(30),
        default="STABLE",
        nullable=False,
    )

    rank: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
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

    skill = relationship("Skill")
    government_unit = relationship("GovernmentUnit")
    source = relationship("LabourMarketSource")

    __table_args__ = (
        Index(
            "ix_emerging_skill_trends_skill",
            "skill_id",
        ),
        Index(
            "ix_emerging_skill_trends_unit_period",
            "government_unit_id",
            "period_start",
            "period_end",
        ),
        Index(
            "ix_emerging_skill_trends_growth",
            "growth_rate",
        ),
    )