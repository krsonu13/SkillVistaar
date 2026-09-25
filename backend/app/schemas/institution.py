from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InstitutionCreate(BaseModel):
    organization_id: UUID
    institution_code: str | None = Field(default=None, max_length=100)
    accreditation_body: str | None = Field(default=None, max_length=255)
    accreditation_number: str | None = Field(default=None, max_length=255)
    institution_type: str | None = Field(default=None, max_length=100)
    description: str | None = None
    website: str | None = Field(default=None, max_length=500)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = None
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    country: str = Field(default="India", max_length=100)


class InstitutionUpdate(BaseModel):
    institution_code: str | None = Field(default=None, max_length=100)
    accreditation_body: str | None = Field(default=None, max_length=255)
    accreditation_number: str | None = Field(default=None, max_length=255)
    institution_type: str | None = Field(default=None, max_length=100)
    description: str | None = None
    website: str | None = Field(default=None, max_length=500)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = None
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)


class InstitutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    institution_code: str | None
    accreditation_body: str | None
    accreditation_number: str | None
    institution_type: str | None
    description: str | None
    website: str | None
    email: str | None
    phone: str | None
    address: str | None
    city: str | None
    state: str | None
    country: str
    verification_status: str
    verified_at: datetime | None
    suspended_at: datetime | None
    revoked_at: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class InstitutionListResponse(BaseModel):
    items: list[InstitutionResponse]
    total: int
    page: int
    page_size: int
    pages: int
