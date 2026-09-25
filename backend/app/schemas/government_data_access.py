from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.government_data_access_authorization import (
    GovernmentDataAccessAuthorizationStatus,
    GovernmentDataAccessLevel,
)


class GovernmentDataAccessAuthorizationCreate(BaseModel):
    """
    Request to grant government-data access to a user.
    """

    user_id: UUID
    government_unit_id: UUID

    access_level: GovernmentDataAccessLevel = Field(
        default=GovernmentDataAccessLevel.VIEW,
    )

    scope: str | None = Field(
        default=None,
        max_length=1000,
    )

    expires_at: datetime | None = None

    reason: str | None = Field(
        default=None,
        max_length=1000,
    )


class GovernmentDataAccessAuthorizationStatusUpdate(BaseModel):
    """
    Request to change the status of a government-data
    access authorization.
    """

    status: GovernmentDataAccessAuthorizationStatus


class GovernmentDataAccessAuthorizationResponse(BaseModel):
    """
    Government-data authorization response.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    user_id: UUID
    government_unit_id: UUID

    access_level: GovernmentDataAccessLevel
    status: GovernmentDataAccessAuthorizationStatus

    scope: str | None
    granted_by_user_id: UUID

    expires_at: datetime | None
    reason: str | None

    created_at: datetime
    updated_at: datetime


class GovernmentDataAccessAuthorizationListResponse(BaseModel):
    """
    Paginated/list response wrapper.
    """

    items: list[
        GovernmentDataAccessAuthorizationResponse
    ]

    total: int