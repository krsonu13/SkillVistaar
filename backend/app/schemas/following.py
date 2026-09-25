from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.following import (
    FollowNotificationPreference,
    FollowTargetType,
)


class FollowingCreate(BaseModel):
    target_type: FollowTargetType
    target_id: UUID | None = None
    target_key: str | None = Field(default=None, max_length=255)
    notification_preference: FollowNotificationPreference = (
        FollowNotificationPreference.ALL
    )


class FollowingUpdate(BaseModel):
    notification_preference: FollowNotificationPreference


class FollowingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    target_type: str
    target_id: UUID | None
    target_key: str | None
    notification_preference: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class FollowingListResponse(BaseModel):
    items: list[FollowingResponse]
    total: int


class FollowingToggleResponse(BaseModel):
    is_following: bool
    following_id: str | None = None
    followers_count: int = 0
    following_count: int = 0