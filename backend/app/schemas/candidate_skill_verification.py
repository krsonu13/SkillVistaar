from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CandidateSkillVerifyRequest(BaseModel):
    notes: str | None = Field(
        default=None,
        max_length=1000,
    )

    expires_at: datetime | None = None


class CandidateSkillRejectRequest(BaseModel):
    notes: str = Field(
        min_length=1,
        max_length=1000,
    )


class CandidateSkillRevokeRequest(BaseModel):
    notes: str = Field(
        min_length=1,
        max_length=1000,
    )