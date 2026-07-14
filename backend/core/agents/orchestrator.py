import logging
import time
from datetime import datetime, timezone
from typing import Any

from core.agents.base import BaseAgent
from core.agents.ingestion_agent import IngestionAgent
from core.agents.extraction_agent import ExtractionAgent
from core.agents.dedup_agent import DedupAgent
from core.agents.priority_agent import PriorityAgent
from core.agents.planning_agent import PlanningAgent
from core.agents.alert_agent import AlertAgent
from core.memory import memory_system
from core.calendar_planner import CalendarPlanner
from core.dependency_analyzer import DependencyAnalyzer
from models.task import Task
from core.normalizer import _infer_team

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    def __init__(self):
        self.agents: list[BaseAgent] = [
            IngestionAgent(),
            ExtractionAgent(),
            DedupAgent(),
            PriorityAgent(),
            PlanningAgent(),
            AlertAgent(),
        ]
        self._shared_memory: dict[str, Any] = {}
        self._pipeline_history: list[dict] = []

    async def run_pipeline(
        self, initial_context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        context = dict(initial_context) if initial_context else {}
        start_time = time.monotonic()
        pipeline_id = f"pipeline_{int(start_time)}"

        logger.info("=== Agentic Pipeline %s: OBSERVE phase ===", pipeline_id)
        context["pipeline_id"] = pipeline_id
        context["_shared_memory"] = self._shared_memory
        context["_start_time"] = start_time
        context["_agent_logs"] = []

        CalendarPlanner.seed_simulated_events()

        for agent in self.agents:
            agent_start = time.monotonic()
            agent_name = agent.name

            logger.info("=== Agent: %s (THINK phase) ===", agent_name)
            try:
                if agent.name == "extraction":
                    self._normalize_inline(context)

                reflection = await agent.reflect(context)
                context.setdefault("_agent_logs", []).append(reflection)
                self._shared_memory[f"{agent_name}_last_reflection"] = reflection

                logger.info("=== Agent: %s (ACT phase) ===", agent_name)
                if agent.name == "ingestion":
                    result = await agent.process(context)
                elif agent.name == "extraction":
                    result = await agent.process(context)
                elif agent.name == "deduplication":
                    result = await agent.process(context)
                elif agent.name == "prioritization":
                    result = await agent.process(context)
                elif agent.name == "planning":
                    result = await agent.process(context)
                elif agent.name == "alert":
                    result = await agent.process(context)
                else:
                    result = await agent.process(context)

                logger.info("=== Agent: %s (VERIFY phase) ===", agent_name)
                verification = await agent.verify(result)
                if not verification.get("verified", True):
                    logger.warning(
                        "Agent %s verification failed: %s", agent_name, verification
                    )

                context.update(result)
                agent_duration = (time.monotonic() - agent_start) * 1000

                self._shared_memory[f"{agent_name}_last_result"] = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "duration_ms": agent_duration,
                    "status": "ok",
                }

                memory_system.record_agent_memory(
                    agent_name,
                    "last_pipeline_result",
                    f"completed in {agent_duration:.0f}ms at {datetime.now(timezone.utc).isoformat()}",
                )

                self._pipeline_history.append(
                    {
                        "pipeline_id": pipeline_id,
                        "agent": agent_name,
                        "duration_ms": agent_duration,
                        "status": "ok",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )

                logger.info("Agent %s finished in %.0fms", agent_name, agent_duration)

            except Exception as e:
                logger.error("Agent %s failed: %s — continuing", agent.name, e)
                self._shared_memory[f"{agent_name}_last_error"] = str(e)
                self._pipeline_history.append(
                    {
                        "pipeline_id": pipeline_id,
                        "agent": agent_name,
                        "duration_ms": (time.monotonic() - agent_start) * 1000,
                        "status": "error",
                        "error": str(e),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )
                import traceback

                traceback.print_exc()

        ranked_tasks = context.get("ranked_tasks", [])
        if ranked_tasks:
            try:
                leverage = DependencyAnalyzer.find_highest_leverage_tasks(ranked_tasks)
                context["highest_leverage_tasks"] = leverage

                unblocking_recs = DependencyAnalyzer.get_unblocking_recommendations(
                    ranked_tasks
                )
                context["unblocking_recommendations"] = unblocking_recs

                deferred = memory_system.detect_deferred_tasks(ranked_tasks)
                context["deferred_tasks_detected"] = deferred

                time_blocked = CalendarPlanner.generate_time_blocked_plan(
                    ranked_tasks[: min(6, len(ranked_tasks))]
                )
                context["time_blocked_plan"] = time_blocked

            except Exception as e:
                logger.warning("Post-processing failed: %s", e)

        self._shared_memory["last_pipeline_run"] = {
            "pipeline_id": pipeline_id,
            "duration_ms": (time.monotonic() - start_time) * 1000,
            "agent_count": len(self.agents),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(
            "=== Pipeline %s complete (%.0fms) ===",
            pipeline_id,
            (time.monotonic() - start_time) * 1000,
        )

        return context

    def _normalize_inline(self, context: dict[str, Any]) -> None:
        try:
            normalized = []
            source_types = [
                "jira",
                "defects",
                "emails",
                "github",
                "slack",
                "transcript",
            ]

            SOURCE_TYPE_MAP = {
                "defects": "defect",
                "emails": "email",
                "jira": "jira",
                "github": "github",
                "slack": "slack",
                "transcript": "transcript",
            }

            for source_type in source_types:
                items = context.get(source_type, [])
                if not items or not isinstance(items, list):
                    continue
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    item_id = item.get("id", "") or item.get("key", "")
                    if not item_id:
                        continue
                    title = item.get("title", "")
                    if source_type == "emails":
                        title = f"Email: {title}" if title else "Email: (no subject)"
                    st = SOURCE_TYPE_MAP.get(
                        source_type, item.get("source_type", source_type)
                    )

                    normalized.append(
                        Task(
                            id=item_id,
                            title=title,
                            description=item.get("description", ""),
                            source=item.get("source", item_id),
                            source_type=st,
                            priority=item.get("priority"),
                            deadline=item.get("deadline"),
                            owner=item.get("owner"),
                            assignee=item.get("owner"),
                            team=_infer_team(item.get("owner")),
                            status=item.get("status") or "open",
                            dependencies=item.get("dependencies", []),
                            blocks=item.get("blocks", []),
                            vp_escalation=item.get("vp_escalation", False),
                            customer_facing=item.get("customer_facing", False),
                            raw_text=str(item.get("raw_text", "") or ""),
                        )
                    )

            context["normalized_tasks"] = normalized
            logger.info("Normalized %d tasks inline", len(normalized))
        except Exception as e:
            logger.error("Inline normalizer failed: %s", e)
            import traceback

            traceback.print_exc()
            context.setdefault("normalized_tasks", [])
