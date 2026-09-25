from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AssessmentCreate(BaseModel):
    organization_id: UUID

    title: str = Field(
        ...,
        min_length=3,
        max_length=200,
    )

    description: str | None = None

    assessment_type: str = Field(
        default="MCQ",
        max_length=40,
    )

    duration_minutes: int = Field(
        default=30,
        ge=1,
        le=480,
    )

    passing_percentage: float = Field(
        default=40.0,
        ge=0,
        le=100,
    )

    max_attempts: int = Field(
        default=1,
        ge=1,
        le=10,
    )

    randomize_questions: bool = True

    show_result_immediately: bool = False

    instructions: str | None = None


class AssessmentUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=3,
        max_length=200,
    )

    description: str | None = None

    assessment_type: str | None = Field(
        default=None,
        max_length=40,
    )

    duration_minutes: int | None = Field(
        default=None,
        ge=1,
        le=480,
    )

    passing_percentage: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    max_attempts: int | None = Field(
        default=None,
        ge=1,
        le=10,
    )

    randomize_questions: bool | None = None

    show_result_immediately: bool | None = None

    instructions: str | None = None


class AssessmentResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: UUID
    organization_id: UUID
    created_by_user_id: UUID

    title: str
    description: str | None

    assessment_type: str

    duration_minutes: int
    total_marks: int
    passing_percentage: float
    max_attempts: int

    randomize_questions: bool
    show_result_immediately: bool

    instructions: str | None

    status: str

    published_at: datetime | None

    created_at: datetime
    updated_at: datetime


class AssessmentListResponse(BaseModel):
    items: list[AssessmentResponse]
    total: int