from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.candidate_credential import (
    CredentialStatus,
    CredentialType,
)


class CandidateCredentialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_profile_id: uuid.UUID
    issuing_organization_id: uuid.UUID | None

    credential_type: CredentialType
    title: str
    credential_number: str | None
    issuing_organization_name: str

    issue_date: datetime | None
    expiry_date: datetime | None

    # Never expose the physical storage path.
    document_hash: str | None

    status: CredentialStatus
    verification_notes: str | None

    verified_by_user_id: uuid.UUID | None
    verified_at: datetime | None

    blockchain_transaction_hash: str | None
    blockchain_network: str | None

    is_public: bool

    created_at: datetime
    updated_at: datetime


class CandidateCredentialListResponse(BaseModel):
    items: list[CandidateCredentialResponse]
    total: int


class CandidateCredentialUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=2,
        max_length=255,
    )

    credential_number: str | None = Field(
        default=None,
        max_length=255,
    )

    issue_date: datetime | None = None
    expiry_date: datetime | None = None
    is_public: bool | None = None


class CandidateCredentialCreate(BaseModel):
    credential_type: CredentialType = CredentialType.CERTIFICATE
    title: str = Field(..., min_length=2, max_length=255)
    credential_number: str | None = Field(default=None, max_length=255)
    issuing_organization_name: str | None = Field(default=None, max_length=255)
    issuer_name: str | None = Field(default=None, max_length=255)
    issue_date: datetime | None = None
    issued_date: datetime | None = None
    expiry_date: datetime | None = None
    document_url: str | None = None
    document_hash: str | None = None
    is_public: bool = True