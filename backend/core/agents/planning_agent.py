import logging
from typing import Any

from core.agents.base import BaseAgent
from core.alert_engine import check_alerts
from core.prioritizer import build_daily_plan_from_tasks
from core.calendar_planner import CalendarPlanner
from core.memory import memory_system
from models.task import DailyPlan

logger = logging.getLogger(__name__)


class PlanningAgent(BaseAgent):
    name = "planning"

    async def process(self, context: dict[str, Any]) -> dict[str, Any]:
        ranked_tasks = context.get("ranked_tasks", [])

        alerts = []
        try:
            alerts = check_alerts(ranked_tasks)
            logger.info("Generated %d alerts", len(alerts))
        except Exception as e:
            logger.error("Alert check failed: %s", e)

        plan = DailyPlan()
        try:
            plan = build_daily_plan_from_tasks(ranked_tasks, alerts)
            logger.info(
                "Built daily plan with %d top priorities", len(plan.top_priorities)
            )
        except Exception as e:
            logger.error("Plan generation failed: %s", e)

        try:
            time_blocks = CalendarPlanner.generate_time_blocked_plan(
                ranked_tasks[: min(6, len(ranked_tasks))]
            )
            if time_blocks:
                plan.time_blocked_plan = time_blocks
                logger.info(
                    "Generated %d time blocks", len(time_blocks.get("time_blocks", []))
                )
        except Exception as e:
            logger.warning("Time-block planning failed: %s", e)

        try:
            memory_system.infer_preferences_from_tasks(ranked_tasks)
        except Exception as e:
            logger.warning("Preference inference failed: %s", e)

        deferred = context.get("deferred_tasks_detected")
        if deferred:
            plan.deferred_tasks_detected = deferred

        leverage = context.get("highest_leverage_tasks")
        if leverage:
            plan.highest_leverage_tasks = leverage

        return {"alerts": alerts, "plan": plan}

    async def reflect(self, context: dict[str, Any]) -> dict[str, Any]:
        reflection = await super().reflect(context)
        ranked = context.get("ranked_tasks", [])
        reflection["observations"] = [f"Planning for {len(ranked)} ranked tasks"]

        calendar_events = CalendarPlanner.get_todays_events()
        if calendar_events:
            reflection["observations"].append(
                f"{len(calendar_events)} calendar events today - planning around them"
            )

        return reflection
