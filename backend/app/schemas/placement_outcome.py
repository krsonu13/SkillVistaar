from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PlacementOutcomeCreate(BaseModel):
    institution_profile_id: UUID
    course_id: UUID | None = None
    government_unit_id: UUID | None = None

    occupation_name: str = Field(..., min_length=2, max_length=200)
    sector: str | None = Field(default=None, max_length=150)

    total_learners: int = Field(default=0, ge=0)
    placed_learners: int = Field(default=0, ge=0)
    employment_rate: float = Field(..., ge=0, le=100)

    average_salary: float | None = Field(default=None, ge=0)
    median_salary: float | None = Field(default=None, ge=0)

    currency: str = Field(default="INR", min_length=3, max_length=3)

    period_start: date
    period_end: date

    source_id: UUID | None = None
    notes: str | None = None

    @field_validator("occupation_name")
    @classmethod
    def normalize_occupation(cls, value: str) -> str:
        return value.strip()

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class PlacementOutcomeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    institution_profile_id: UUID
    course_id: UUID | None
    government_unit_id: UUID | None

    occupation_name: str
    sector: str | None

    total_learners: int
    placed_learners: int
    employment_rate: float

    average_salary: float | None
    median_salary: float | None
    currency: str

    period_start: date
    period_end: date

    source_id: UUID | None
    notes: str | None

    created_at: datetime
    updated_at: datetime


class PlacementOutcomeSummaryResponse(BaseModel):
    record_count: int
    total_learners: int
    placed_learners: int
    overall_employment_rate: float
    average_salary: float | None


class PlacementOutcomeListResponse(BaseModel):
    items: list[PlacementOutcomeResponse]
    total: int