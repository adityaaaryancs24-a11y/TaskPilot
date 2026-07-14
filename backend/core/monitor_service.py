import asyncio
import logging
import os
from datetime import datetime, timezone
from dateutil import parser as dp

from core.state import store
from core.agent import run_pipeline
from core.notification_service import notification_service
from core.alert_service import alert_service

logger = logging.getLogger(__name__)

STALE_THRESHOLD_MINUTES = 30
HEALTH_INTERVAL = 60
DEADLINE_INTERVAL = 120
STALE_CHECK_INTERVAL = 180


class MonitorService:
    def __init__(self):
        self._tasks: dict[str, asyncio.Task] = {}
        self._running = False
        self._pipeline_lock = asyncio.Lock()

    async def start(self):
        if self._running:
            return
        self._running = True
        logger.info("Monitor service starting")

        self._tasks = {
            "health": asyncio.create_task(self._health_loop()),
            "deadlines": asyncio.create_task(self._deadline_watch_loop()),
            "stale": asyncio.create_task(self._stale_detection_loop()),
        }

        await alert_service.start()

    async def stop(self):
        self._running = False
        for name, task in self._tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks.clear()
        await alert_service.stop()
        logger.info("Monitor service stopped")

    async def ensure_pipeline_fresh(self, reason: str = "auto") -> bool:
        async with self._pipeline_lock:
            try:
                await asyncio.wait_for(run_pipeline(), timeout=120)
                logger.info("Auto-refresh completed (reason: %s)", reason)
                return True
            except asyncio.TimeoutError:
                logger.error("Auto-refresh timed out after 120s (reason: %s)", reason)
                return False
            except Exception as e:
                logger.error("Auto-refresh failed (reason: %s): %s", reason, e)
                return False

    async def _health_loop(self):
        while self._running:
            try:
                status = self._collect_health_status()
                await notification_service.broadcast_status_now(status)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Health check error: %s", e)
            await asyncio.sleep(HEALTH_INTERVAL)

    async def _deadline_watch_loop(self):
        while self._running:
            try:
                self._check_approaching_deadlines()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Deadline watch error: %s", e)
            await asyncio.sleep(DEADLINE_INTERVAL)

    async def _stale_detection_loop(self):
        while self._running:
            try:
                if self._is_pipeline_stale():
                    logger.warning(
                        "Pipeline stale (>%d min since last run) — auto-refreshing",
                        STALE_THRESHOLD_MINUTES,
                    )
                    await self.ensure_pipeline_fresh(reason="stale_detection")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Stale detection error: %s", e)
            await asyncio.sleep(STALE_CHECK_INTERVAL)

    def _is_pipeline_stale(self) -> bool:
        if not store.last_run_timestamp:
            return True
        last = datetime.fromisoformat(store.last_run_timestamp)
        elapsed = (datetime.now(timezone.utc) - last).total_seconds() / 60
        return elapsed > STALE_THRESHOLD_MINUTES

    def _check_approaching_deadlines(self):
        tasks = store.current_tasks
        if not tasks:
            return
        now = datetime.now(timezone.utc)
        urgent: list[str] = []
        for t in tasks:
            if t.status == "done" or not t.deadline:
                continue
            try:
                dl = dp.parse(t.deadline)
                if dl.tzinfo is None:
                    dl = dl.replace(tzinfo=timezone.utc)
                remaining_h = (dl - now).total_seconds() / 3600
                if 0 < remaining_h <= 4:
                    urgent.append(
                        f'{t.id} ("{t.title[:40]}") due in ~{int(remaining_h)}h'
                    )
            except Exception:
                continue
        if urgent:
            logger.warning("Urgent deadlines approaching: %s", "; ".join(urgent))

    def _collect_health_status(self) -> dict:
        task_count = len(store.current_tasks)
        has_plan = store.current_plan is not None
        last_run = store.last_run_timestamp or "never"
        llm_key = bool(
            os.environ.get("LLM_API_KEY") or os.environ.get("XAI_API_KEY", "")
        )

        from core.observability import get_connector_status

        connectors = get_connector_status()
        connected_count = sum(1 for c in connectors if c.get("connected", False))
        total_connectors = len(connectors)

        return {
            "status": "healthy",
            "task_count": task_count,
            "has_plan": has_plan,
            "last_pipeline_run": last_run,
            "llm_available": llm_key,
            "connectors_connected": f"{connected_count}/{total_connectors}",
            "connectors": connectors,
            "stale": self._is_pipeline_stale(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


monitor_service = MonitorService()
