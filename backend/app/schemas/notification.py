from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    notification_type: str
    priority: str
    title: str
    message: str
    title_mr: str | None
    message_mr: str | None
    translation_key: str | None
    translation_params: dict | None
    entity_type: str | None
    entity_id: UUID | None
    action_url: str | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    unread_count: int


class NotificationPreferenceUpdate(BaseModel):
    preference: str = Field(
        default="ALL",
        pattern="^(ALL|IMPORTANT_ONLY|MUTED)$",
    )
    enabled_email: bool = True
    enabled_sms: bool = False
    enabled_push: bool = True


class NotificationPreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    notification_type: str
    preference: str
    enabled_email: bool
    enabled_sms: bool
    enabled_push: bool


class NotificationPreferenceListResponse(BaseModel):
    items: list[NotificationPreferenceResponse]
