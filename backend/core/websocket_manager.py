import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self._connections: dict[str, set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str = "broadcast"):
        await websocket.accept()
        self._connections.setdefault(channel, set()).add(websocket)
        logger.info(
            "WebSocket connected to channel '%s' (%d total)",
            channel,
            len(self._connections[channel]),
        )

    def disconnect(self, websocket: WebSocket, channel: str = "broadcast"):
        self._connections.get(channel, set()).discard(websocket)
        logger.info("WebSocket disconnected from channel '%s'", channel)

    async def broadcast(self, channel: str, event: str, data: Any):
        payload = json.dumps({"event": event, "data": data}, default=str)
        connections = self._connections.get(channel)
        if not connections:
            return
        dead = set()
        for ws in list(connections):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)
        if dead:
            connections.difference_update(dead)

    async def broadcast_alerts(self, alerts: list[dict]):
        await self.broadcast("broadcast", "alerts_updated", alerts)

    async def broadcast_priorities(self, tasks: list[dict]):
        await self.broadcast("broadcast", "priorities_updated", tasks)

    async def broadcast_task_list(self, tasks: list[dict]):
        await self.broadcast("broadcast", "tasks_updated", tasks)

    async def broadcast_plan(self, plan: dict):
        await self.broadcast("broadcast", "plan_updated", plan)


ws_manager = WebSocketManager()
