from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate_profile import CandidateProfile
from app.models.conversation import Conversation, ConversationStatus
from app.models.government_unit import GovernmentUnit
from app.models.message import Message
from app.models.notification import NotificationPriority, NotificationType
from app.models.organization import Organization
from app.models.user import User
from app.schemas.messaging import (
    ConversationDetailResponse,
    ConversationParticipant,
    ConversationResponse,
    MessageResponse,
    UnreadCountsResponse,
)
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class MessagingError(Exception):
    """Base exception for messaging system."""
    pass


class ConversationNotFoundError(MessagingError):
    pass


class MessagingPermissionError(MessagingError):
    pass


class MessagingValidationError(MessagingError):
    pass


class MessagingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _resolve_participant(self, user_id: UUID) -> ConversationParticipant:
        """Resolve rich participant details from User, CandidateProfile, Organization, or GovernmentUnit."""
        user = await self.db.get(User, user_id)
        if not user:
            return ConversationParticipant(
                id=user_id,
                username=None,
                name="Unknown User",
                account_type="CANDIDATE",
                avatar=None,
                headline=None,
            )

        username = user.username
        name = user.username or "User"
        avatar = None
        headline = None

        if user.account_type == "CANDIDATE":
            res = await self.db.execute(
                select(CandidateProfile).where(CandidateProfile.user_id == user.id).limit(1)
            )
            cp = res.scalar_one_or_none()
            if cp:
                full_name = f"{cp.first_name} {cp.last_name or ''}".strip()
                if full_name:
                    name = full_name
                avatar = cp.profile_photo_path
                headline = cp.headline
        elif user.account_type in ("EMPLOYER", "TRAINING_INSTITUTE"):
            res = await self.db.execute(
                select(Organization).where(Organization.owner_user_id == user.id).limit(1)
            )
            org = res.scalar_one_or_none()
            if org:
                name = org.display_name or org.legal_name or name
                avatar = org.logo_path
                headline = f"Verified {user.account_type.replace('_', ' ').title()}"
        elif user.account_type == "GOVERNMENT":
            if user.government_unit_id:
                gu = await self.db.get(GovernmentUnit, user.government_unit_id)
                if gu:
                    name = gu.name
                    headline = f"Government Authority ({gu.level.title()})"

        return ConversationParticipant(
            id=user.id,
            username=username,
            name=name,
            account_type=user.account_type,
            avatar=avatar,
            headline=headline,
        )

    async def get_or_create_conversation(
        self,
        current_user_id: UUID,
        recipient_id: UUID,
    ) -> tuple[Conversation, bool]:
        """Fetch existing conversation or create a new one between two users."""
        if current_user_id == recipient_id:
            raise MessagingValidationError("You cannot start a conversation with yourself.")

        recipient = await self.db.get(User, recipient_id)
        if not recipient or not recipient.is_active or recipient.is_suspended:
            raise MessagingValidationError("Recipient user is not available on SkillVistaar.")

        user_a_id = min(current_user_id, recipient_id)
        user_b_id = max(current_user_id, recipient_id)

        stmt = select(Conversation).where(
            Conversation.user_a_id == user_a_id,
            Conversation.user_b_id == user_b_id,
        ).limit(1)
        res = await self.db.execute(stmt)
        conv = res.scalar_one_or_none()

        if conv is not None:
            return conv, False

        new_conv = Conversation(
            user_a_id=user_a_id,
            user_b_id=user_b_id,
            initiator_user_id=current_user_id,
            recipient_user_id=recipient_id,
            status=ConversationStatus.REQUESTED.value,
        )
        self.db.add(new_conv)
        await self.db.flush()
        return new_conv, True

    async def send_message(
        self,
        current_user: User,
        recipient_id: UUID,
        content: str,
    ) -> Message:
        clean_content = content.strip()
        if not clean_content:
            raise MessagingValidationError("Message content cannot be blank.")

        conv, created = await self.get_or_create_conversation(current_user.id, recipient_id)

        # Check if conversation was previously rejected
        if conv.status == ConversationStatus.REJECTED.value:
            if conv.recipient_user_id == current_user.id:
                # The user who previously rejected is now replying -> automatically accept
                conv.status = ConversationStatus.ACCEPTED.value
            else:
                raise MessagingPermissionError(
                    "Your previous message request was declined by the recipient."
                )

        now = datetime.now(timezone.utc)
        message = Message(
            conversation_id=conv.id,
            sender_id=current_user.id,
            recipient_id=recipient_id,
            content=clean_content,
            is_read=False,
            created_at=now,
        )
        self.db.add(message)

        conv.last_message_text = clean_content[:200]
        conv.last_message_at = now

        await self.db.commit()
        await self.db.refresh(message)

        # Dispatch notification to recipient
        try:
            notif_svc = NotificationService(self.db)
            sender_handle = f"@{current_user.username}" if current_user.username else "Someone"
            if created or conv.status == ConversationStatus.REQUESTED.value:
                await notif_svc.create_notification(
                    user_id=recipient_id,
                    notification_type=NotificationType.MESSAGE_REQUEST,
                    title=f"Message Request from {sender_handle}",
                    message=f"{sender_handle} sent you a direct message request.",
                    priority=NotificationPriority.NORMAL,
                    action_url="/messages?tab=requests",
                )
            else:
                await notif_svc.create_notification(
                    user_id=recipient_id,
                    notification_type=NotificationType.MESSAGE_RECEIVED,
                    title=f"New message from {sender_handle}",
                    message=f"{sender_handle}: {clean_content[:120]}",
                    priority=NotificationPriority.NORMAL,
                    action_url=f"/messages?conversation={conv.id}",
                )
        except Exception as exc:
            logger.warning("Failed to emit messaging notification: %s", exc)

        return message

    async def list_conversations(
        self,
        current_user_id: UUID,
        folder: str = "inbox",
    ) -> list[ConversationResponse]:
        """
        List conversations for current user.
        - folder='inbox': All accepted conversations, plus conversations the user initiated
        - folder='requests': Incoming conversations where status='REQUESTED' and current user is recipient
        """
        is_participant = or_(
            Conversation.user_a_id == current_user_id,
            Conversation.user_b_id == current_user_id,
        )

        if folder.lower() == "requests":
            stmt = select(Conversation).where(
                Conversation.recipient_user_id == current_user_id,
                Conversation.status == ConversationStatus.REQUESTED.value,
            ).order_by(Conversation.created_at.desc())
        else:
            # Inbox: Accepted conversations OR conversations initiated by user (waiting on other party)
            stmt = select(Conversation).where(
                is_participant,
                or_(
                    Conversation.status == ConversationStatus.ACCEPTED.value,
                    Conversation.initiator_user_id == current_user_id,
                ),
            ).order_by(Conversation.last_message_at.desc().nullslast(), Conversation.created_at.desc())

        res = await self.db.execute(stmt)
        conversations = res.scalars().all()

        responses: list[ConversationResponse] = []
        for conv in conversations:
            other_id = conv.user_b_id if conv.user_a_id == current_user_id else conv.user_a_id
            other_part = await self._resolve_participant(other_id)

            # Unread messages in this conversation
            unread_stmt = select(func.count(Message.id)).where(
                Message.conversation_id == conv.id,
                Message.recipient_id == current_user_id,
                Message.is_read == False,
            )
            unread_count = (await self.db.execute(unread_stmt)).scalar() or 0

            responses.append(
                ConversationResponse(
                    id=conv.id,
                    other_user=other_part,
                    status=conv.status,
                    last_message_text=conv.last_message_text,
                    last_message_at=conv.last_message_at,
                    unread_count=unread_count,
                    is_initiator=(conv.initiator_user_id == current_user_id),
                    created_at=conv.created_at,
                )
            )

        return responses

    async def get_conversation_detail(
        self,
        current_user_id: UUID,
        conversation_id: UUID,
    ) -> ConversationDetailResponse:
        conv = await self.db.get(Conversation, conversation_id)
        if not conv:
            raise ConversationNotFoundError("Conversation not found.")

        if current_user_id not in (conv.user_a_id, conv.user_b_id):
            raise MessagingPermissionError("You are not a participant in this conversation.")

        # Mark all messages received by current_user as read
        now = datetime.now(timezone.utc)
        await self.db.execute(
            update(Message)
            .where(
                Message.conversation_id == conv.id,
                Message.recipient_id == current_user_id,
                Message.is_read == False,
            )
            .values(is_read=True, read_at=now)
        )
        await self.db.commit()

        # Fetch messages
        msg_stmt = (
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.asc())
        )
        msg_res = await self.db.execute(msg_stmt)
        messages_db = msg_res.scalars().all()

        message_responses = [
            MessageResponse(
                id=m.id,
                conversation_id=m.conversation_id,
                sender_id=m.sender_id,
                recipient_id=m.recipient_id,
                content=m.content,
                is_read=m.is_read,
                read_at=m.read_at,
                created_at=m.created_at,
                is_mine=(m.sender_id == current_user_id),
            )
            for m in messages_db
        ]

        other_id = conv.user_b_id if conv.user_a_id == current_user_id else conv.user_a_id
        other_part = await self._resolve_participant(other_id)

        return ConversationDetailResponse(
            id=conv.id,
            other_user=other_part,
            status=conv.status,
            last_message_text=conv.last_message_text,
            last_message_at=conv.last_message_at,
            unread_count=0,
            is_initiator=(conv.initiator_user_id == current_user_id),
            created_at=conv.created_at,
            messages=message_responses,
        )

    async def get_or_create_by_other_user(
        self,
        current_user_id: UUID,
        other_user_id: UUID,
    ) -> ConversationDetailResponse:
        conv, _ = await self.get_or_create_conversation(current_user_id, other_user_id)
        await self.db.commit()
        return await self.get_conversation_detail(current_user_id, conv.id)

    async def accept_request(
        self,
        current_user_id: UUID,
        conversation_id: UUID,
    ) -> ConversationResponse:
        conv = await self.db.get(Conversation, conversation_id)
        if not conv:
            raise ConversationNotFoundError("Conversation not found.")

        if conv.recipient_user_id != current_user_id:
            raise MessagingPermissionError("Only the recipient can accept a message request.")

        conv.status = ConversationStatus.ACCEPTED.value
        await self.db.commit()
        await self.db.refresh(conv)

        other_id = conv.user_b_id if conv.user_a_id == current_user_id else conv.user_a_id
        other_part = await self._resolve_participant(other_id)

        return ConversationResponse(
            id=conv.id,
            other_user=other_part,
            status=conv.status,
            last_message_text=conv.last_message_text,
            last_message_at=conv.last_message_at,
            unread_count=0,
            is_initiator=(conv.initiator_user_id == current_user_id),
            created_at=conv.created_at,
        )

    async def reject_request(
        self,
        current_user_id: UUID,
        conversation_id: UUID,
    ) -> ConversationResponse:
        conv = await self.db.get(Conversation, conversation_id)
        if not conv:
            raise ConversationNotFoundError("Conversation not found.")

        if conv.recipient_user_id != current_user_id:
            raise MessagingPermissionError("Only the recipient can decline a message request.")

        conv.status = ConversationStatus.REJECTED.value
        await self.db.commit()
        await self.db.refresh(conv)

        other_id = conv.user_b_id if conv.user_a_id == current_user_id else conv.user_a_id
        other_part = await self._resolve_participant(other_id)

        return ConversationResponse(
            id=conv.id,
            other_user=other_part,
            status=conv.status,
            last_message_text=conv.last_message_text,
            last_message_at=conv.last_message_at,
            unread_count=0,
            is_initiator=(conv.initiator_user_id == current_user_id),
            created_at=conv.created_at,
        )

    async def get_unread_counts(self, current_user_id: UUID) -> UnreadCountsResponse:
        # Total unread messages
        unread_msg_stmt = select(func.count(Message.id)).where(
            Message.recipient_id == current_user_id,
            Message.is_read == False,
        )
        unread_messages = (await self.db.execute(unread_msg_stmt)).scalar() or 0

        # Total pending incoming requests
        pending_req_stmt = select(func.count(Conversation.id)).where(
            Conversation.recipient_user_id == current_user_id,
            Conversation.status == ConversationStatus.REQUESTED.value,
        )
        pending_requests = (await self.db.execute(pending_req_stmt)).scalar() or 0

        return UnreadCountsResponse(
            unread_messages_count=unread_messages,
            pending_requests_count=pending_requests,
        )
