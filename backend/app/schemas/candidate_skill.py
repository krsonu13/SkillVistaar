from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.candidate_skill import (
    CandidateSkillProficiency,
    CandidateSkillStatus,
)


class CandidateSkillCreate(BaseModel):
    skill_id: uuid.UUID

    proficiency_level: CandidateSkillProficiency = (
        CandidateSkillProficiency.BEGINNER
    )

    years_of_experience: float = Field(
        default=0,
        ge=0,
        le=100,
    )

    is_primary: bool = False


class CandidateSkillUpdate(BaseModel):
    proficiency_level: CandidateSkillProficiency | None = None

    years_of_experience: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    is_primary: bool | None = None


class CandidateSkillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_profile_id: uuid.UUID
    skill_id: uuid.UUID

    proficiency_level: CandidateSkillProficiency
    years_of_experience: float
    status: CandidateSkillStatus
    is_primary: bool

    verified_by_user_id: uuid.UUID | None
    verified_at: datetime | None
    expires_at: datetime | None
    verification_notes: str | None

    created_at: datetime
    updated_at: datetime


class CandidateSkillStatusUpdate(BaseModel):
    status: CandidateSkillStatus
    verification_notes: str | None = Field(
        default=None,
        max_length=1000,
    )


class CandidateSkillListResponse(BaseModel):
    items: list[CandidateSkillResponse]
    total: int