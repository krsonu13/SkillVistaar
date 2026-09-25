from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AssessmentAttemptCreate(BaseModel):
    """
    Candidate starts a new attempt.

    The invitation_id is enough to identify the assessment
    and candidate. The backend must validate both.
    """

    invitation_id: UUID


class AssessmentAttemptStartResponse(BaseModel):
    """
    Returned when an attempt starts.

    The candidate receives the server-controlled expiry time
    rather than being trusted to calculate the timer locally.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    invitation_id: UUID
    assessment_id: UUID
    candidate_profile_id: UUID

    attempt_number: int
    status: str

    started_at: datetime | None
    expires_at: datetime | None

    total_questions: int


class AssessmentAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    invitation_id: UUID
    assessment_id: UUID
    candidate_profile_id: UUID

    attempt_number: int
    status: str

    started_at: datetime | None
    submitted_at: datetime | None
    expires_at: datetime | None

    total_questions: int
    answered_questions: int
    correct_answers: int
    wrong_answers: int
    unanswered_questions: int

    total_marks: float
    obtained_marks: float
    percentage: float
    passed: bool | None

    created_at: datetime
    updated_at: datetime


class AssessmentAttemptListResponse(BaseModel):
    items: list[AssessmentAttemptResponse]
    total: int


class AssessmentAttemptSubmitResponse(BaseModel):
    """
    Returned after submission.

    Contains the final result but does not expose
    the correct answers themselves.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    invitation_id: UUID
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


class AssessmentAttemptCandidateQuestion(BaseModel):
    """
    Question delivered during an active attempt.

    Correct answer and explanation are NEVER included.
    """

    id: UUID
    question_text: str
    question_type: str
    difficulty: str

    options: list[str] | None = None

    marks: int
    negative_marks: float

    skill_id: UUID | None = None
    sequence_number: int

    # Candidate's current answer, if already saved.
    answer_text: str | None = None


class AssessmentAttemptSessionResponse(BaseModel):
    """
    Complete active assessment session returned to the candidate.
    """

    attempt: AssessmentAttemptStartResponse
    questions: list[AssessmentAttemptCandidateQuestion]

    server_time: datetime
    expires_at: datetime | None