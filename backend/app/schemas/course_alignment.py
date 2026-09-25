from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CourseAlignmentCreate(BaseModel):
    course_id: UUID
    skill_id: UUID
    government_unit_id: UUID | None = None

    demand_score: float = Field(..., ge=0, le=100)
    skill_coverage_score: float = Field(..., ge=0, le=100)
    alignment_score: float = Field(..., ge=0, le=100)

    alignment_status: str = Field(
        default="PARTIALLY_ALIGNED",
        max_length=30,
    )

    recommended_action: str | None = Field(
        default=None,
        max_length=1000,
    )


class CourseAlignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    course_id: UUID
    skill_id: UUID
    government_unit_id: UUID | None

    demand_score: float
    skill_coverage_score: float
    alignment_score: float

    alignment_status: str
    recommended_action: str | None

    analyzed_at: datetime
    created_at: datetime
    updated_at: datetime


class CourseAlignmentListResponse(BaseModel):
    items: list[CourseAlignmentResponse]
    total: int