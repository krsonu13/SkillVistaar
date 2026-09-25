from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AssessmentInvitationCreate(BaseModel):
    assessment_id: UUID
    job_application_id: UUID

    expires_at: datetime | None = None

    message: str | None = Field(
        default=None,
        max_length=2000,
    )


class AssessmentInvitationStatusUpdate(BaseModel):
    status: str = Field(
        ...,
        max_length=30,
    )


class AssessmentInvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assessment_id: UUID
    job_application_id: UUID
    candidate_profile_id: UUID
    invited_by_user_id: UUID

    status: str
    message: str | None

    invited_at: datetime
    expires_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None

    is_active: bool
    created_at: datetime
    updated_at: datetime


class AssessmentInvitationCandidateResponse(BaseModel):
    """
    Safe response for candidates.

    Employer/internal information is intentionally excluded.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assessment_id: UUID
    status: str

    message: str | None

    invited_at: datetime
    expires_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None

    is_active: bool


class AssessmentInvitationListResponse(BaseModel):
    items: list[AssessmentInvitationResponse]
    total: int


class AssessmentInvitationCandidateListResponse(BaseModel):
    items: list[AssessmentInvitationCandidateResponse]
    total: int