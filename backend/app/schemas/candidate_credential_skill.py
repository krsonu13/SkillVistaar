from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CandidateCredentialSkillCreate(BaseModel):
    skill_id: uuid.UUID
    is_primary: bool = False


class CandidateCredentialSkillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    credential_id: uuid.UUID
    skill_id: uuid.UUID
    is_primary: bool
    created_at: datetime
    updated_at: datetime


class CandidateCredentialSkillListResponse(BaseModel):
    items: list[CandidateCredentialSkillResponse]
    total: int


class CandidateCredentialSkillRemoveResponse(BaseModel):
    message: str = Field(
        default="Credential-skill mapping removed successfully."
    )