from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class VerifierAuthorizationCreate(BaseModel):
    verifier_user_id: UUID
    application_type: str = Field(min_length=1, max_length=50)
    government_unit_id: UUID | None = None


class VerifierAuthorizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    verifier_user_id: UUID
    government_unit_id: UUID | None
    application_type: str
    granted_by_user_id: UUID
    is_active: bool
    granted_at: datetime
    revoked_at: datetime | None
    created_at: datetime
    updated_at: datetime