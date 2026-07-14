import logging
from typing import Any

from core.agents.base import BaseAgent
from core.prioritizer import prioritize, split_by_owner
from core.dependency_analyzer import DependencyAnalyzer
from models.task import RankedTask

logger = logging.getLogger(__name__)


class PriorityAgent(BaseAgent):
    name = "prioritization"

    async def process(self, context: dict[str, Any]) -> dict[str, Any]:
        deduped_tasks = context.get("deduped_tasks", [])

        my_tasks, delegated_tasks = split_by_owner(deduped_tasks)

        if delegated_tasks:
            logger.info(
                "Filtered out %d delegated tasks (owned by others)",
                len(delegated_tasks),
            )

        try:
            ranked_tasks = await prioritize(my_tasks)
            logger.info(
                "Prioritized %d tasks (%d delegated excluded)",
                len(ranked_tasks),
                len(delegated_tasks),
            )
        except Exception as e:
            logger.error("Prioritization failed: %s", e)
            ranked_tasks = [
                RankedTask(
                    **t.model_dump(
                        exclude={"rank", "score", "rationale", "score_breakdown"}
                    ),
                    score=50.0,
                    rationale="Fallback ranking.",
                )
                for t in my_tasks
            ]

        leverage = DependencyAnalyzer.find_highest_leverage_tasks(my_tasks)
        if leverage:
            logger.info(
                "Highest leverage task: %s (score: %.1f)",
                leverage[0]["task_id"],
                leverage[0]["leverage_score"],
            )

        return {"ranked_tasks": ranked_tasks, "delegated_tasks": delegated_tasks}

    async def reflect(self, context: dict[str, Any]) -> dict[str, Any]:
        reflection = await super().reflect(context)
        ranked = context.get("ranked_tasks", [])
        reflection["observations"] = [
            f"Scored {len(ranked)} tasks using deterministic 7-factor formula"
        ]

        if ranked:
            top = ranked[0]
            reflection["observations"].append(
                f"Top task: {top.id} ({top.title[:40]}) score={top.score}"
            )
            if top.score_breakdown:
                biggest = max(top.score_breakdown, key=top.score_breakdown.get)
                reflection["decisions"] = [
                    f"Biggest score driver: {biggest}={top.score_breakdown[biggest]}"
                ]

        return reflection
