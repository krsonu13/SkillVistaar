from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.job_screening_question import ScreeningQuestionType


class JobScreeningQuestionCreate(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=2000,
    )

    question_type: ScreeningQuestionType

    options: list[str] | None = None

    is_required: bool = True

    display_order: int = Field(
        default=0,
        ge=0,
    )


class JobScreeningQuestionUpdate(BaseModel):
    question: str | None = Field(
        default=None,
        min_length=3,
        max_length=2000,
    )

    question_type: ScreeningQuestionType | None = None

    options: list[str] | None = None

    is_required: bool | None = None

    display_order: int | None = Field(
        default=None,
        ge=0,
    )


class JobScreeningQuestionResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: UUID
    job_id: UUID
    question: str
    question_type: ScreeningQuestionType
    options: list[str] | None
    is_required: bool
    display_order: int
    created_at: datetime
    updated_at: datetime


class JobScreeningQuestionListResponse(BaseModel):
    items: list[JobScreeningQuestionResponse]
    total: int
