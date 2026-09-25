from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.job_application import ApplicationStatus


class JobApplicationCreate(BaseModel):
    cover_letter: str | None = Field(default=None, max_length=5000)
    resume_document_id: UUID | None = None
    consent_to_share_profile: bool = False

    @field_validator("cover_letter")
    @classmethod
    def clean_cover_letter(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class JobApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus
    reason: str | None = Field(default=None, max_length=2000)

    @field_validator("reason")
    @classmethod
    def clean_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class JobApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    candidate_profile_id: UUID
    candidate_user_id: UUID
    status: ApplicationStatus
    cover_letter: str | None
    resume_document_id: UUID | None
    match_score: float
    matched_required_skills: int
    total_required_skills: int
    matched_preferred_skills: int
    total_preferred_skills: int
    consent_to_share_profile: bool
    applied_at: datetime
    updated_at: datetime


class JobApplicationListResponse(BaseModel):
    applications: list[JobApplicationResponse] = Field(default_factory=list)
    items: list[JobApplicationResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50
    pages: int = 1
