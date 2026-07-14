import asyncio
import json
import logging
from typing import Any

from core.websocket_manager import ws_manager
from models.task import Task

logger = logging.getLogger(__name__)


def _as_json(obj: Any) -> Any:
    if isinstance(obj, Task):
        return obj.model_dump(mode="json")
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    return obj


class NotificationService:
    def __init__(self):
        self._debounce_timer: asyncio.TimerHandle | None = None
        self._pending: dict[str, Any] = {}
        self._last_alerts_hash: str = ""
        self._last_tasks_hash: str = ""
        self._broadcast_lock = asyncio.Lock()

    def _hash(self, data: Any) -> str:
        raw = json.dumps(data, default=str, sort_keys=True)
        return str(hash(raw))

    def _coalesced_dispatch(self):
        pending = self._pending
        self._pending = {}

        if self._running_loop():
            asyncio.create_task(self._dispatch_all(pending))

    async def _dispatch_all(self, pending: dict[str, Any]):
        try:
            if "plan" in pending:
                plan_data = _as_json(pending["plan"])
                await ws_manager.broadcast_plan(plan_data)

            if "tasks" in pending:
                tasks_data = [_as_json(t) for t in pending["tasks"]]
                async with self._broadcast_lock:
                    h = self._hash(tasks_data)
                    if h != self._last_tasks_hash:
                        self._last_tasks_hash = h
                        await ws_manager.broadcast_task_list(tasks_data)
                        await ws_manager.broadcast_priorities(tasks_data)

            if "alerts" in pending:
                alerts_data = [_as_json(a) for a in pending["alerts"]]
                async with self._broadcast_lock:
                    h = self._hash(alerts_data)
                    if h != self._last_alerts_hash:
                        self._last_alerts_hash = h
                        await ws_manager.broadcast_alerts(alerts_data)

            narrative = pending.get("narrative")
            if narrative:
                await ws_manager.broadcast("broadcast", "narrative_alert", narrative)
        except Exception as e:
            logger.warning("Notification dispatch failed: %s", e)

    def schedule(self, **changes: Any):
        self._pending.update(changes)
        if self._debounce_timer:
            self._debounce_timer.cancel()
        if self._running_loop():
            self._debounce_timer = asyncio.get_running_loop().call_later(
                0.5, self._coalesced_dispatch
            )

    @staticmethod
    def _running_loop() -> bool:
        try:
            asyncio.get_running_loop()
            return True
        except RuntimeError:
            return False

    async def broadcast_alerts_now(self, alerts: list):
        alerts_data = [_as_json(a) for a in alerts]
        async with self._broadcast_lock:
            h = self._hash(alerts_data)
            if h != self._last_alerts_hash:
                self._last_alerts_hash = h
                await ws_manager.broadcast_alerts(alerts_data)

    async def broadcast_status_now(self, status: dict[str, Any]):
        await ws_manager.broadcast("broadcast", "system_status", status)


notification_service = NotificationService()
