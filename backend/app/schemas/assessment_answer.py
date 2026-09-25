from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AssessmentAnswerCreate(BaseModel):
    """Candidate submits or updates an answer."""

    question_id: UUID

    answer_text: str | None = Field(
        default=None,
        max_length=10000,
    )


class AssessmentAnswerUpdate(BaseModel):
    """Candidate updates an existing answer."""

    answer_text: str | None = Field(
        default=None,
        max_length=10000,
    )


class AssessmentAnswerResponse(BaseModel):
    """
    Safe answer response.

    Evaluation fields are intentionally excluded from the
    candidate-facing API.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    attempt_id: UUID
    question_id: UUID

    answer_text: str | None
    is_answered: bool
    answered_at: datetime | None

    created_at: datetime
    updated_at: datetime


class AssessmentAnswerResultResponse(BaseModel):
    """
    Result response used after submission.

    This can be exposed only when the assessment configuration
    allows the candidate to see results.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    attempt_id: UUID
    question_id: UUID

    answer_text: str | None
    is_answered: bool
    is_correct: bool | None
    marks_awarded: float

    answered_at: datetime | None
    evaluated_at: datetime | None

    created_at: datetime
    updated_at: datetime


class AssessmentAnswerListResponse(BaseModel):
    items: list[AssessmentAnswerResponse]
    total: int


class AssessmentAnswerResultListResponse(BaseModel):
    items: list[AssessmentAnswerResultResponse]
    total: int