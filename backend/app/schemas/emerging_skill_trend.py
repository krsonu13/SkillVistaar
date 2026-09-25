from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EmergingSkillTrendCreate(BaseModel):
    skill_id: UUID
    government_unit_id: UUID | None = None
    source_id: UUID | None = None

    demand_count: int = Field(default=0, ge=0)
    growth_rate: float = Field(default=0, ge=-100, le=1000)
    trend_direction: str = Field(default="STABLE", max_length=30)
    rank: int | None = Field(default=None, ge=1)

    period_start: datetime
    period_end: datetime


class EmergingSkillTrendResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    skill_id: UUID
    government_unit_id: UUID | None
    source_id: UUID | None

    demand_count: int
    growth_rate: float
    trend_direction: str
    rank: int | None

    period_start: datetime
    period_end: datetime

    created_at: datetime
    updated_at: datetime


class EmergingSkillTrendListResponse(BaseModel):
    items: list[EmergingSkillTrendResponse]
    total: int