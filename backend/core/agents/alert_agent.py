import logging
from typing import Any

from core.agents.base import BaseAgent
from core.alert_engine import check_alerts

logger = logging.getLogger(__name__)


class AlertAgent(BaseAgent):
    name = "alert"

    async def process(self, context: dict[str, Any]) -> dict[str, Any]:
        ranked_tasks = context.get("ranked_tasks", [])

        try:
            alerts = check_alerts(ranked_tasks)
            logger.info("Generated %d alerts", len(alerts))
        except Exception as e:
            logger.error("Alert check failed: %s", e)
            alerts = []

        return {"alerts": alerts}

    async def reflect(self, context: dict[str, Any]) -> dict[str, Any]:
        reflection = await super().reflect(context)
        ranked = context.get("ranked_tasks", [])
        alerts = check_alerts(ranked) if ranked else []

        critical = [a for a in alerts if a.severity == "critical"]
        warnings = [a for a in alerts if a.severity == "warning"]

        reflection["observations"] = [
            f"Generated {len(alerts)} alerts ({len(critical)} critical, {len(warnings)} warnings)"
        ]

        if critical:
            reflection["decisions"] = [
                f"Critical alerts require immediate attention: {', '.join(a.message[:50] for a in critical[:3])}"
            ]

        return reflection
