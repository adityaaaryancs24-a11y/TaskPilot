import asyncio
import hashlib
import json
import logging

from core.alert_engine import check_alerts
from core.state import store
from core.notification_service import notification_service

logger = logging.getLogger(__name__)


def _alert_signature(alerts: list[dict]) -> str:
    raw = json.dumps(
        sorted(
            (a.get("severity", ""), a.get("message", ""), a.get("task_id", ""))
            for a in alerts
        ),
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class AlertService:
    def __init__(self):
        self._task: asyncio.Task | None = None
        self._running = False
        self._last_signature: str = ""
        self._interval = 30

    async def start(self):
        if self._running:
            return
        self._running = True
        logger.info("Alert service starting (interval=%ds)", self._interval)
        self._task = asyncio.create_task(self._alert_loop())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("Alert service stopped")

    def evaluate(self) -> list[dict]:
        try:
            tasks = store.current_tasks
            if not tasks:
                return []
            return [a.model_dump(mode="json") for a in check_alerts(tasks)]
        except Exception as e:
            logger.error("Alert evaluation failed: %s", e)
            return []

    def has_new_alerts(self, alerts: list[dict]) -> bool:
        sig = _alert_signature(alerts)
        if sig != self._last_signature:
            self._last_signature = sig
            return True
        return False

    async def _alert_loop(self):
        while self._running:
            try:
                alerts = self.evaluate()
                if alerts and self.has_new_alerts(alerts):
                    logger.info(
                        "New alert state detected (%d active alerts)", len(alerts)
                    )
                    critical = [a for a in alerts if a.get("severity") == "critical"]
                    if critical:
                        logger.warning("Broadcasting %d critical alerts", len(critical))
                    await notification_service.broadcast_alerts_now(alerts)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Alert loop error: %s", e)
            await asyncio.sleep(self._interval)


alert_service = AlertService()
