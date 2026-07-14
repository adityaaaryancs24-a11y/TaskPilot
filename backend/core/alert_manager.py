from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlertManager:
    def __init__(self):
        self.channels: list[dict[str, Any]] = []
        self.rules: list[dict[str, Any]] = []

    def add_channel(self, channel_type: str, config: dict[str, Any]):
        self.channels.append({"type": channel_type, "config": config})

    def add_rule(self, rule: dict[str, Any]):
        self.rules.append(rule)

    def set_rules(self, rules: list[dict[str, Any]]):
        self.rules = rules

    async def send_alert(
        self,
        severity: AlertSeverity,
        title: str,
        message: str,
        context: Optional[dict[str, Any]] = None,
    ):
        logger.info("Alert [%s] %s: %s", severity.value, title, message)
        for channel in self.channels:
            try:
                if channel["type"] == "slack":
                    await self._send_slack(
                        channel["config"], severity, title, message, context
                    )
                elif channel["type"] == "webhook":
                    await self._send_webhook(
                        channel["config"], severity, title, message, context
                    )
                elif channel["type"] == "log":
                    self._send_log(severity, title, message)
            except Exception as e:
                logger.warning("Failed to send alert to %s: %s", channel["type"], e)

    async def _send_slack(
        self,
        config: dict[str, Any],
        severity: AlertSeverity,
        title: str,
        message: str,
        context: Optional[dict[str, Any]] = None,
    ):
        import aiohttp

        color_map = {
            AlertSeverity.CRITICAL: "danger",
            AlertSeverity.WARNING: "warning",
            AlertSeverity.INFO: "good",
        }
        fields = [
            {"title": "Severity", "value": severity.value, "short": True},
            {
                "title": "Timestamp",
                "value": str(datetime.now(timezone.utc)),
                "short": True,
            },
        ]
        if context:
            for key, val in context.items():
                fields.append({"title": key, "value": str(val), "short": True})
        payload = {
            "attachments": [
                {
                    "color": color_map.get(severity, "warning"),
                    "title": f"[{severity.value.upper()}] {title}",
                    "text": message,
                    "fields": fields,
                    "footer": "TaskPilot AI Monitoring",
                }
            ]
        }
        async with aiohttp.ClientSession() as session:
            await session.post(config["webhook_url"], json=payload)

    async def _send_webhook(
        self,
        config: dict[str, Any],
        severity: AlertSeverity,
        title: str,
        message: str,
        context: Optional[dict[str, Any]] = None,
    ):
        import aiohttp

        payload = {
            "severity": severity.value,
            "title": title,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context": context or {},
        }
        async with aiohttp.ClientSession() as session:
            await session.post(config["url"], json=payload)

    def _send_log(self, severity: AlertSeverity, title: str, message: str):
        fn = {
            "critical": logger.critical,
            "warning": logger.warning,
            "info": logger.info,
        }
        fn.get(severity.value, logger.info)(
            "[%s] %s: %s", severity.value.upper(), title, message
        )


alert_manager = AlertManager()

ALERT_RULES = [
    {
        "name": "pipeline_failure",
        "condition": "pipeline_runs_failure_rate > 0.1",
        "severity": AlertSeverity.CRITICAL,
        "message": "Pipeline failure rate exceeded 10%",
    },
    {
        "name": "high_llm_latency",
        "condition": "llm_latency_p95 > 5",
        "severity": AlertSeverity.WARNING,
        "message": "LLM p95 latency exceeded 5 seconds",
    },
    {
        "name": "db_connection_pool_exhausted",
        "condition": "db_connections_active > db_connections_max * 0.9",
        "severity": AlertSeverity.CRITICAL,
        "message": "Database connection pool > 90% utilized",
    },
    {
        "name": "queue_growth",
        "condition": "queue_length > 100",
        "severity": AlertSeverity.WARNING,
        "message": "Queue length exceeded 100 items",
    },
]

alert_manager.add_channel("log", {})
slack_url = os.environ.get("SLACK_WEBHOOK_URL")
if slack_url:
    alert_manager.add_channel("slack", {"webhook_url": slack_url})
alert_manager.set_rules(ALERT_RULES)
