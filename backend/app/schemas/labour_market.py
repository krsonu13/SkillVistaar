from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LabourMarketSourceCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    source_type: str = Field(..., max_length=50)
    organization_name: str | None = Field(default=None, max_length=200)
    description: str | None = None
    source_url: str | None = Field(default=None, max_length=1000)
    collection_method: str | None = Field(default=None, max_length=100)
    reliability_score: float | None = Field(default=None, ge=0, le=100)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return value.strip()


class LabourMarketSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    source_type: str
    organization_name: str | None
    description: str | None
    source_url: str | None
    collection_method: str | None
    reliability_score: float | None
    is_verified: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LabourMarketSnapshotCreate(BaseModel):
    government_unit_id: UUID | None = None
    source_id: UUID | None = None
    skill_id: UUID | None = None

    occupation_code: str | None = Field(default=None, max_length=100)
    occupation_name: str = Field(..., min_length=2, max_length=200)
    sector: str | None = Field(default=None, max_length=150)

    employment_type: str | None = Field(default=None, max_length=50)
    workplace_type: str | None = Field(default=None, max_length=50)

    experience_min: float | None = Field(default=None, ge=0)
    experience_max: float | None = Field(default=None, ge=0)

    demand_count: int = Field(default=0, ge=0)
    supply_count: int = Field(default=0, ge=0)

    average_salary: float | None = Field(default=None, ge=0)
    median_salary: float | None = Field(default=None, ge=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)

    period_start: datetime
    period_end: datetime

    notes: str | None = None

    @field_validator("occupation_name")
    @classmethod
    def validate_occupation_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class LabourMarketSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    government_unit_id: UUID | None
    source_id: UUID | None
    skill_id: UUID | None

    occupation_code: str | None
    occupation_name: str
    sector: str | None
    employment_type: str | None
    workplace_type: str | None

    experience_min: float | None
    experience_max: float | None

    demand_count: int
    supply_count: int

    average_salary: float | None
    median_salary: float | None
    currency: str

    period_start: datetime
    period_end: datetime

    notes: str | None
    created_at: datetime
    updated_at: datetime


class LabourMarketSummaryResponse(BaseModel):
    total_demand: int
    total_supply: int
    demand_supply_gap: int
    records: int


class LabourMarketSnapshotListResponse(BaseModel):
    items: list[LabourMarketSnapshotResponse]
    total: int