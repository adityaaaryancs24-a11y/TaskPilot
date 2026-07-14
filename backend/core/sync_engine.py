import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from core.state import save_trace
from core.connector_registry import connector_registry
from core.agent import run_pipeline
from core.memory import memory_system

logger = logging.getLogger(__name__)

SCHEDULES: dict[str, int] = {
    "slack": 60,
    "outlook": 120,
    "jira": 300,
    "github": 300,
    "servicenow": 300,
    "transcript": 600,
}


class SyncEngine:
    def __init__(self):
        self._tasks: dict[str, asyncio.Task] = {}
        self._running = False
        self._last_event_count: dict[str, int] = {}

    async def start(self):
        if self._running:
            return
        self._running = True
        logger.info("Sync engine starting with schedules: %s", SCHEDULES)

        for source_type, connector in connector_registry.items():
            interval = SCHEDULES.get(source_type, 300)
            self._tasks[source_type] = asyncio.create_task(
                self._sync_loop(source_type, connector, interval)
            )

    async def stop(self):
        self._running = False
        for name, task in self._tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks.clear()
        logger.info("Sync engine stopped")

    async def _sync_loop(self, source_type: str, connector, interval: int):
        while self._running:
            try:
                await self._sync_once(source_type, connector)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Sync loop %s error: %s", source_type, e)
            await asyncio.sleep(interval)

    async def _sync_once(self, source_type: str, connector) -> bool:
        start = datetime.now(timezone.utc)
        try:
            connected = await connector.connect()
            if not connected:
                logger.warning("Connector %s not connected, skipping sync", source_type)
                return False

            raw = await connector.fetch_tasks()
            if raw:
                event_count = len(raw)
                prev_count = self._last_event_count.get(source_type, 0)
                self._last_event_count[source_type] = event_count

                logger.info("Synced %d items from %s", len(raw), source_type)
                connector.last_sync = start.isoformat()

                if event_count != prev_count:
                    logger.info(
                        "New data detected from %s (%d -> %d) — reprioritizing",
                        source_type,
                        prev_count,
                        event_count,
                    )
                    await run_pipeline()
                    memory_system.record_agent_memory(
                        "sync_engine",
                        f"last_detected_change_{source_type}",
                        f"{prev_count}->{event_count} at {datetime.now(timezone.utc).isoformat()}",
                    )
                else:
                    logger.info(
                        "No changes in %s (still %d items)", source_type, event_count
                    )
            return True
        except Exception as e:
            logger.error("Sync failed for %s: %s", source_type, e)
            connector.error = str(e)
            return False
        finally:
            elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            await save_trace(f"sync_{source_type}", elapsed, status="ok")

    async def sync_now(self, source_type: Optional[str] = None):
        if source_type:
            connector = connector_registry.get(source_type)
            if connector:
                await self._sync_once(source_type, connector)
        else:
            for source_type, connector in connector_registry.items():
                await self._sync_once(source_type, connector)


sync_engine = SyncEngine()
