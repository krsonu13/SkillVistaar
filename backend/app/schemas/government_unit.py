from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GovernmentUnitBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    unit_type: str = Field(..., min_length=1, max_length=100)
    level: int = Field(..., ge=1, le=10)
    description: str | None = None
    status: str = Field(default="ACTIVE", max_length=40)
    jurisdiction: str | None = Field(default=None, max_length=255)
    parent_id: UUID | None = None


class GovernmentUnitCreate(GovernmentUnitBase):
    pass


class GovernmentUnitUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: str | None = Field(default=None, max_length=40)
    jurisdiction: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class GovernmentUnitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    unit_type: str
    level: int
    description: str | None = None
    is_active: bool
    status: str
    jurisdiction: str | None = None
    parent_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class GovernmentUnitNode(BaseModel):
    id: str
    code: str
    name: str
    unit_type: str
    level: int
    status: str
    jurisdiction: str | None = None
    parent_id: str | None = None
    children: list[GovernmentUnitNode] = Field(default_factory=list)
