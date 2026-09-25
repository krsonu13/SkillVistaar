from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.verification_application import VerificationStatus


class VerificationApplicationCreate(BaseModel):
    applicant_user_id: UUID
    government_unit_id: UUID | None = None
    application_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )
    submitted_data: dict | None = None
    remarks: str | None = Field(
        default=None,
        max_length=2000,
    )


class VerificationApplicationReview(BaseModel):
    status: str = Field(
        ...,
        min_length=1,
        max_length=50,
    )
    reason: str | None = Field(
        default=None,
        max_length=2000,
    )
    remarks: str | None = Field(
        default=None,
        max_length=2000,
    )


class VerificationApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    applicant_user_id: UUID
    verifier_user_id: UUID | None
    government_unit_id: UUID | None

    status: str
    application_type: str

    submitted_data: dict | None
    remarks: str | None
    rejection_reason: str | None

    created_at: datetime
    updated_at: datetime


class VerificationApplicationStatusUpdate(BaseModel):
    status: VerificationStatus
    reason: str | None = Field(
        default=None,
        max_length=2000,
    )
    remarks: str | None = Field(
        default=None,
        max_length=2000,
    )


class VerificationApplicationResubmit(BaseModel):
    submitted_data: dict | None = None
    remarks: str | None = Field(
        default=None,
        max_length=2000,
    )