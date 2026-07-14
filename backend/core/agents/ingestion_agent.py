import logging
from typing import Any

from core.agents.base import BaseAgent
from core.connector_registry import connector_registry

logger = logging.getLogger(__name__)


class IngestionAgent(BaseAgent):
    name = "ingestion"

    async def process(self, context: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {
            "jira": [],
            "defects": [],
            "emails": [],
            "transcript": [],
            "github": [],
            "slack": [],
        }

        for source_type, connector in connector_registry.items():
            try:
                await connector.connect()
                raw = await connector.fetch_tasks()
                if raw:
                    result[source_type] = raw
                    connector.last_sync = (
                        __import__("datetime")
                        .datetime.now(__import__("datetime").timezone.utc)
                        .isoformat()
                    )
                else:
                    logger.info(
                        "Connector %s returned 0 tasks (live API up, no data)",
                        source_type,
                    )
            except Exception as e:
                logger.warning(
                    "Connector %s failed: %s — skipping (live API only)", source_type, e
                )
                connector.error = str(e)

        total_count = sum(len(v) for v in result.values())
        self.remember("last_ingestion_count", str(total_count))

        return result

    async def reflect(self, context: dict[str, Any]) -> dict[str, Any]:
        reflection = await super().reflect(context)

        connector_statuses = []
        for source_type, connector in connector_registry.items():
            status = (
                "connected"
                if connector.connected
                else f"error: {connector.error or 'unknown'}"
            )
            connector_statuses.append(f"{source_type}={status}")

        reflection["observations"] = [f"Connectors: {', '.join(connector_statuses)}"]

        return reflection
