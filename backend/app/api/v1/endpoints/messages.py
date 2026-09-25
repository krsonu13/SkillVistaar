from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.messaging import (
    ConversationDetailResponse,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
    UnreadCountsResponse,
)
from app.services.messaging_service import (
    ConversationNotFoundError,
    MessagingPermissionError,
    MessagingService,
    MessagingValidationError,
)

router = APIRouter(
    prefix="/messages",
    tags=["Messaging"],
)


@router.post(
    "/send",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    payload: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Send a direct message to a platform user.
    If this is the first contact, a Conversation is created in REQUESTED state.
    """
    svc = MessagingService(db)
    try:
        msg = await svc.send_message(
            current_user=current_user,
            recipient_id=payload.recipient_id,
            content=payload.content,
        )
        return MessageResponse(
            id=msg.id,
            conversation_id=msg.conversation_id,
            sender_id=msg.sender_id,
            recipient_id=msg.recipient_id,
            content=msg.content,
            is_read=msg.is_read,
            read_at=msg.read_at,
            created_at=msg.created_at,
            is_mine=True,
        )
    except MessagingValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except MessagingPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/conversations",
    response_model=list[ConversationResponse],
)
async def list_conversations(
    folder: str = Query("inbox", pattern="^(inbox|requests)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    List conversations.
    - folder='inbox': Active conversations and outgoing requests.
    - folder='requests': Incoming direct message requests pending review.
    """
    svc = MessagingService(db)
    return await svc.list_conversations(current_user.id, folder=folder)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
)
async def get_conversation_detail(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Fetch message thread for a conversation and mark incoming messages as read.
    """
    svc = MessagingService(db)
    try:
        return await svc.get_conversation_detail(current_user.id, conversation_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MessagingPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/with-user/{user_id}",
    response_model=ConversationDetailResponse,
)
async def get_or_create_conversation_with_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get or initialize a conversation thread with a specific user.
    """
    svc = MessagingService(db)
    try:
        return await svc.get_or_create_by_other_user(current_user.id, user_id)
    except MessagingValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/conversations/{conversation_id}/accept",
    response_model=ConversationResponse,
)
async def accept_message_request(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Accept an incoming message request. The conversation moves to the primary inbox.
    """
    svc = MessagingService(db)
    try:
        return await svc.accept_request(current_user.id, conversation_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MessagingPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post(
    "/conversations/{conversation_id}/reject",
    response_model=ConversationResponse,
)
async def reject_message_request(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Decline an incoming message request.
    """
    svc = MessagingService(db)
    try:
        return await svc.reject_request(current_user.id, conversation_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MessagingPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/unread-counts",
    response_model=UnreadCountsResponse,
)
async def get_unread_counts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get unread message badge count and pending requests count.
    """
    svc = MessagingService(db)
    return await svc.get_unread_counts(current_user.id)
