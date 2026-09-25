from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OrgDocumentCreate(BaseModel):
    document_type: str = Field(..., min_length=2, max_length=80)
    title: str = Field(..., min_length=2, max_length=255)
    document_number: str | None = Field(default=None, max_length=100)
    issuing_authority: str | None = Field(default=None, max_length=255)
    issue_date: date | None = None
    expiry_date: date | None = None
    file_name: str | None = Field(default=None, max_length=255)
    file_url: str | None = Field(default=None, max_length=500)
    file_size: int | None = None
    mime_type: str | None = Field(default=None, max_length=100)
    document_id: UUID | None = None


class OrgDocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    document_number: str | None = Field(default=None, max_length=100)
    issuing_authority: str | None = Field(default=None, max_length=255)
    issue_date: date | None = None
    expiry_date: date | None = None


class OrgDocumentAction(BaseModel):
    action: str = Field(
        ...,
        description="START_REVIEW, APPROVE, REJECT, REQUEST_INFORMATION, REVOKE",
    )
    remarks: str | None = None
    reason: str | None = None


class OrgDocumentHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    actor_user_id: UUID | None = None
    action: str
    previous_status: str | None = None
    new_status: str
    remarks: str | None = None
    reason: str | None = None
    created_at: datetime


class OrgDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    document_id: UUID | None = None
    document_type: str
    title: str
    document_number: str | None = None
    issuing_authority: str | None = None
    issue_date: date | None = None
    expiry_date: date | None = None
    file_name: str | None = None
    file_url: str | None = None
    file_size: int | None = None
    mime_type: str | None = None
    status: str
    uploaded_by_user_id: UUID
    verifier_user_id: UUID | None = None
    verification_remarks: str | None = None
    rejection_reason: str | None = None
    verified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    history: list[OrgDocumentHistoryResponse] = []
