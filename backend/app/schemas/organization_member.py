from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.organization_member import OrganizationMemberRole


class OrganizationMemberCreate(BaseModel):
    user_id: uuid.UUID
    role_code: OrganizationMemberRole


class OrganizationMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID
    role_code: OrganizationMemberRole
    invited_by_user_id: uuid.UUID | None
    is_active: bool
    joined_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime
    updated_at: datetime


class OrganizationMemberRevokeRequest(BaseModel):
    role_code: OrganizationMemberRole