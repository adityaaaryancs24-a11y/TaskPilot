import logging

from core.connector_registry import connector_registry

logger = logging.getLogger(__name__)


async def load_jira() -> list[dict]:
    connector = connector_registry.get("jira")
    if connector:
        try:
            await connector.connect()
            return await connector.fetch_tasks()
        except Exception as e:
            logger.warning("Jira connector failed: %s", e)
    return []


async def load_defects() -> list[dict]:
    connector = connector_registry.get("defects")
    if connector:
        try:
            await connector.connect()
            return await connector.fetch_tasks()
        except Exception as e:
            logger.warning("ServiceNow connector failed: %s", e)
    return []


async def load_emails() -> list[dict]:
    connector = connector_registry.get("emails")
    if connector:
        try:
            await connector.connect()
            return await connector.fetch_tasks()
        except Exception as e:
            logger.warning("Outlook connector failed: %s", e)
    return []


async def load_transcript() -> str:
    return ""
