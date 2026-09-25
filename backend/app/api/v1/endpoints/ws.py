from __future__ import annotations

import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.core.events import event_manager
from app.core.security import decode_access_token, get_current_user
from app.db.session import AsyncSessionLocal
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Real-time"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str | None = Query(None),
):
    """
    Real-time bidirectional WebSocket connection.
    Authenticates via JWT token query param (?token=<access_token>) or first auth message.
    Broadcasts real-time notifications, messages, verification status updates, and follow events.
    """
    user_id: UUID | None = None

    if token:
        try:
            payload = decode_access_token(token)
            raw_sub = payload.get("sub")
            if raw_sub:
                user_id = UUID(str(raw_sub))
        except Exception as e:
            logger.warning("WebSocket token validation failed: %s", e)
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    if not user_id:
        # Allow client to send initial auth packet
        await websocket.accept()
        try:
            raw_msg = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
            data = json.loads(raw_msg)
            if data.get("type") == "AUTH" and data.get("token"):
                payload = decode_access_token(data["token"])
                user_id = UUID(str(payload["sub"]))
            else:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
        except Exception:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    else:
        # Token was already verified from query param
        await websocket.accept()

    # Validate that user exists and is active in DB
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))
        user = res.scalar_one_or_none()
        if not user or user.is_suspended:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    # Register socket
    async with event_manager._lock:
        if user_id not in event_manager.active_connections:
            event_manager.active_connections[user_id] = set()
        event_manager.active_connections[user_id].add(websocket)

    logger.info("Realtime WebSocket connected for user %s", user_id)

    # Send initial connected handshake
    try:
        await websocket.send_text(json.dumps({"type": "CONNECTED", "data": {"user_id": str(user_id)}}))
    except Exception:
        await event_manager.disconnect(websocket, user_id)
        return

    try:
        while True:
            msg = await websocket.receive_text()
            # Handle heartbeat ping
            if msg == "ping":
                await websocket.send_text("pong")
            else:
                try:
                    parsed = json.loads(msg)
                    if parsed.get("type") == "PING":
                        await websocket.send_text(json.dumps({"type": "PONG"}))
                except Exception:
                    pass
    except WebSocketDisconnect:
        await event_manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.debug("WebSocket error: %s", e)
        await event_manager.disconnect(websocket, user_id)


@router.get("/events")
async def sse_events(
    token: str = Query(...),
):
    """
    Server-Sent Events (SSE) fallback endpoint for environments where WebSockets are unavailable.
    """
    try:
        payload = decode_access_token(token)
        user_id = UUID(str(payload.get("sub")))
    except Exception:
        return StreamingResponse(
            iter(["event: error\ndata: Unauthorized\n\n"]),
            media_type="text/event-stream",
            status_code=401,
        )

    queue: asyncio.Queue[str] = asyncio.Queue()

    class SseSocketAdapter:
        async def send_text(self, text: str):
            await queue.put(text)

    fake_ws = SseSocketAdapter()  # type: ignore

    async with event_manager._lock:
        if user_id not in event_manager.active_connections:
            event_manager.active_connections[user_id] = set()
        event_manager.active_connections[user_id].add(fake_ws)  # type: ignore

    async def event_generator():
        try:
            yield f"event: connected\ndata: {json.dumps({'user_id': str(user_id)})}\n\n"
            while True:
                data = await queue.get()
                yield f"event: message\ndata: {data}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            async with event_manager._lock:
                if user_id in event_manager.active_connections:
                    event_manager.active_connections[user_id].discard(fake_ws)  # type: ignore
                    if not event_manager.active_connections[user_id]:
                        del event_manager.active_connections[user_id]

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
