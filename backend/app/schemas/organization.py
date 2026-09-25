from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class OrganizationCreate(BaseModel):
    legal_name: str = Field(..., min_length=2, max_length=255)
    display_name: str | None = Field(default=None, max_length=255)
    organization_type: str = Field(..., pattern="^(EMPLOYER|TRAINING_INSTITUTE)$")
    registration_number: str | None = Field(default=None, max_length=150)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    website: str | None = Field(default=None, max_length=500)
    address: str | None = None
    description: str | None = None
    government_unit_id: UUID | None = None

    # Institution specifics (optional if training institute)
    institution_code: str | None = None
    accreditation_body: str | None = None
    accreditation_number: str | None = None
    city: str | None = None
    state: str | None = None


class OrganizationReview(BaseModel):
    status: str = Field(
        ...,
        pattern="^(APPROVED|REJECTED|SUSPENDED|REVOKED|MORE_INFORMATION_REQUIRED)$",
    )
    remarks: str | None = Field(default=None, max_length=2000)
    rejection_reason: str | None = Field(default=None, max_length=2000)


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_user_id: UUID
    government_unit_id: UUID | None = None
    organization_type: str
    legal_name: str
    display_name: str | None = None
    registration_number: str | None = None
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    address: str | None = None
    description: str | None = None
    verification_status: str
    is_active: bool
    verified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
