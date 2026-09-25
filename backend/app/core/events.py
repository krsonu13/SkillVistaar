from __future__ import annotations

import asyncio
import json
import logging
from typing import Any
from uuid import UUID

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class EventManager:
    """
    Manages active WebSocket connections for real-time bidirectional/push updates.
    Supports targeting individual users (multiple tabs/devices per user),
    broadcasting to groups of users, and global broadcasts.
    """

    def __init__(self) -> None:
        # Maps user_id -> set of active WebSockets
        self.active_connections: dict[UUID, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: UUID) -> None:
        await websocket.accept()
        async with self._lock:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()
            self.active_connections[user_id].add(websocket)
        logger.info("WebSocket connected for user %s (total sockets for user: %d)", user_id, len(self.active_connections[user_id]))

    async def disconnect(self, websocket: WebSocket, user_id: UUID) -> None:
        async with self._lock:
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
        logger.info("WebSocket disconnected for user %s", user_id)

    async def send_to_user(self, user_id: UUID, event_type: str, data: dict[str, Any]) -> None:
        """
        Send an event payload to all active connections of a specific user.
        """
        payload = json.dumps({"type": event_type, "data": data}, default=str)
        sockets_to_send: list[WebSocket] = []

        async with self._lock:
            if user_id in self.active_connections:
                sockets_to_send = list(self.active_connections[user_id])

        dead_sockets: list[WebSocket] = []
        for socket in sockets_to_send:
            try:
                await socket.send_text(payload)
            except Exception as e:
                logger.warning("Error sending WebSocket message to user %s: %s", user_id, e)
                dead_sockets.append(socket)

        if dead_sockets:
            async with self._lock:
                if user_id in self.active_connections:
                    for s in dead_sockets:
                        self.active_connections[user_id].discard(s)
                    if not self.active_connections[user_id]:
                        del self.active_connections[user_id]

    async def broadcast_to_users(self, user_ids: list[UUID] | set[UUID], event_type: str, data: dict[str, Any]) -> None:
        """
        Send an event to a specified list or set of users.
        """
        for uid in user_ids:
            await self.send_to_user(uid, event_type, data)

    async def broadcast(self, event_type: str, data: dict[str, Any]) -> None:
        """
        Global broadcast to all connected clients across the entire platform.
        """
        payload = json.dumps({"type": event_type, "data": data}, default=str)
        async with self._lock:
            all_sockets = [
                (uid, sock)
                for uid, sockets in self.active_connections.items()
                for sock in sockets
            ]

        for uid, socket in all_sockets:
            try:
                await socket.send_text(payload)
            except Exception as e:
                logger.warning("Error broadcasting WebSocket message to user %s: %s", uid, e)


# Global singleton instance
event_manager = EventManager()
