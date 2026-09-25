from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AssessmentResultResponse(BaseModel):
    """
    Backward-compatible general assessment result response.

    Used by the existing result service and can also be used by
    future result-list APIs.
    """

    model_config = ConfigDict(from_attributes=True)

    attempt_id: UUID
    invitation_id: UUID
    assessment_id: UUID
    candidate_profile_id: UUID

    attempt_number: int
    status: str

    total_questions: int
    answered_questions: int
    correct_answers: int
    wrong_answers: int
    unanswered_questions: int

    total_marks: float
    obtained_marks: float
    percentage: float
    passed: bool | None

    started_at: datetime | None
    submitted_at: datetime | None
    expires_at: datetime | None


class AssessmentResultSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    attempt_id: UUID
    assessment_id: UUID
    attempt_number: int
    status: str

    submitted_at: datetime | None

    total_questions: int
    answered_questions: int
    correct_answers: int
    wrong_answers: int
    unanswered_questions: int

    total_marks: float
    obtained_marks: float
    percentage: float
    passed: bool | None


class AssessmentResultAnswer(BaseModel):
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


class AssessmentResultAnswerListResponse(BaseModel):
    items: list[AssessmentResultAnswer]
    total: int


class AssessmentResultQuestion(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    question_text: str
    question_type: str
    options: list[str] | None
    marks: float
    negative_marks: float
    skill_id: UUID | None
    sequence_number: int


class AssessmentDetailedResult(BaseModel):
    summary: AssessmentResultSummary
    questions: list[AssessmentResultQuestion]
    answers: list[AssessmentResultAnswer]


class AssessmentEmployerResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    attempt_id: UUID
    assessment_id: UUID
    candidate_profile_id: UUID

    attempt_number: int
    status: str
    submitted_at: datetime | None

    total_questions: int
    answered_questions: int
    correct_answers: int
    wrong_answers: int
    unanswered_questions: int

    total_marks: float
    obtained_marks: float
    percentage: float
    passed: bool | None