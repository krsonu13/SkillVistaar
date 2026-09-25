from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LabourMarketSourceType(str, Enum):
    GOVERNMENT = "GOVERNMENT"
    JOB_POSTINGS = "JOB_POSTINGS"
    EMPLOYER_SURVEY = "EMPLOYER_SURVEY"
    INDUSTRY_CONSULTATION = "INDUSTRY_CONSULTATION"
    PLACEMENT_DATA = "PLACEMENT_DATA"
    TRAINING_INSTITUTE = "TRAINING_INSTITUTE"
    RESEARCH = "RESEARCH"
    OTHER = "OTHER"


class LabourMarketSource(Base):
    __tablename__ = "labour_market_sources"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    organization_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    source_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    collection_method: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    reliability_score: Mapped[float | None] = mapped_column(
        nullable=True,
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
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

    __table_args__ = (
        Index(
            "ix_labour_market_sources_type_active",
            "source_type",
            "is_active",
        ),
        Index(
            "ix_labour_market_sources_verified",
            "is_verified",
        ),
    )