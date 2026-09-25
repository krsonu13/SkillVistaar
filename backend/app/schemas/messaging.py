from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MessageCreate(BaseModel):
    recipient_id: UUID
    content: str = Field(..., min_length=1, max_length=5000)


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    sender_id: UUID
    recipient_id: UUID
    content: str
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime
    is_mine: bool = False

    model_config = ConfigDict(from_attributes=True)


class ConversationParticipant(BaseModel):
    id: UUID
    username: str | None = None
    name: str
    account_type: str
    avatar: str | None = None
    headline: str | None = None


class ConversationResponse(BaseModel):
    id: UUID
    other_user: ConversationParticipant
    status: str
    last_message_text: str | None = None
    last_message_at: datetime | None = None
    unread_count: int = 0
    is_initiator: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailResponse(BaseModel):
    id: UUID
    other_user: ConversationParticipant
    status: str
    last_message_text: str | None = None
    last_message_at: datetime | None = None
    unread_count: int = 0
    is_initiator: bool = False
    created_at: datetime
    messages: list[MessageResponse] = []


class UnreadCountsResponse(BaseModel):
    unread_messages_count: int
    pending_requests_count: int
