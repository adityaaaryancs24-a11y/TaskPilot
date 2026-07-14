from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from core.llm_client import call_llm
from core.prompts import build_daily_plan_prompt
from core.scoring_engine import DeterministicScoringEngine
from core.tracer import trace
from core.memory import memory_system
from core.dependency_analyzer import DependencyAnalyzer
from models.task import Task, DailyPlan, RankedTask, Alert

logger = logging.getLogger(__name__)

_SELF_OWNER_TOKENS = {"you", "me", "i", "myself", "the engineer", "inbox owner"}
_TEAM_TOKENS = {
    "team",
    "dev",
    "frontend",
    "backend",
    "ai",
    "qa",
    "security",
    "oncall",
    "design",
}


def _is_my_task(task: Task) -> bool:
    # Treat unowned tasks as mine (inbox)
    if task.owner is None and task.assignee is None:
        return True
    # Check if explicitly assigned to me via assignee field
    if task.assignee and "alex" in task.assignee.strip().lower():
        return True
    if task.owner is None:
        return True
    owner_lower = task.owner.strip().lower()
    if owner_lower in _SELF_OWNER_TOKENS:
        return True
    owner_parts = (
        owner_lower.replace("@", " ").replace(".", " ").replace("-", " ").split()
    )
    for part in owner_parts:
        if part in _TEAM_TOKENS:
            return True
    return False


def split_by_owner(tasks: list[Task]) -> tuple[list[Task], list[Task]]:
    mine, delegated = [], []
    for t in tasks:
        (mine if _is_my_task(t) else delegated).append(t)
    return mine, delegated


def _task_to_scoring_dict(task: Task) -> dict[str, Any]:
    return {
        "id": task.id,
        "title": task.title,
        "source": task.source,
        "source_type": task.source_type,
        "priority": task.priority or "unknown",
        "deadline": task.deadline,
        "owner": task.owner,
        "status": task.status,
        "dependencies": task.dependencies,
        "blocks": task.blocks,
        "vp_escalation": task.vp_escalation,
        "customer_facing": task.customer_facing,
        "merged_sources": task.merged_sources,
    }


def _apply_preference_boosts(ranked: list[RankedTask]) -> list[RankedTask]:
    boosts = memory_system.get_preference_boosts()
    if not boosts:
        return ranked

    keyword_map = {
        "prefer_security": ["security", "audit", "token", "vulnerability", "encrypt"],
        "prefer_ui_bugs": ["ui", "dashboard", "safari", "render", "chart", "dark mode"],
        "prefer_backend": [
            "database",
            "migration",
            "api",
            "sync",
            "websocket",
            "backend",
        ],
        "prefer_performance": ["memory", "leak", "latency", "performance", "timeout"],
        "prefer_integrations": ["github", "jira", "slack", "connector", "sync"],
        "prefer_refactors": ["refactor", "cleanup", "docs", "documentation", "test"],
    }

    for rt in ranked:
        title_lower = rt.title.lower()
        for pref, multiplier in boosts.items():
            if pref in keyword_map:
                keywords = keyword_map[pref]
                if any(kw in title_lower for kw in keywords):
                    rt.score = round(rt.score * multiplier, 1)
    ranked.sort(key=lambda t: t.score, reverse=True)
    return ranked


@trace("prioritization")
async def prioritize(tasks: list[Task]) -> list[RankedTask]:
    if not tasks:
        return []

    ranked = DeterministicScoringEngine.score_tasks(tasks)

    ranked = _apply_preference_boosts(ranked)

    memory_system.infer_preferences_from_tasks(tasks)

    leverage = DependencyAnalyzer.find_highest_leverage_tasks(tasks)
    if leverage:
        logger.info("Highest leverage tasks: %s", [l["task_id"] for l in leverage])

    return ranked


async def get_daily_plan(
    ranked_tasks: list[RankedTask],
    active_alerts: Optional[list[dict[str, Any]]] = None,
) -> str:
    if not ranked_tasks:
        return "## Top 3 for Today\n\nNo tasks found.\n"

    task_dicts = [
        _task_to_scoring_dict(t) | {"score": t.score, "rationale": t.rationale}
        for t in ranked_tasks
    ]
    system, user_prompt = build_daily_plan_prompt(task_dicts, active_alerts)

    try:
        response = await call_llm(
            prompt=user_prompt,
            system=system,
            json_mode=False,
            temperature=0.3,
            max_output_tokens=2048,
        )
        return response.text.strip()
    except Exception:
        return _fallback_daily_plan(ranked_tasks)


def _fallback_daily_plan(ranked_tasks: list[RankedTask]) -> str:
    lines = ["## Top 3 for Today\n"]
    for t in ranked_tasks[:3]:
        lines.append(f"- **{t.title}** (score: {t.score:.1f}) — {t.rationale}")
    lines.append("\n## Do Next\n")
    for t in ranked_tasks[3:7]:
        lines.append(f"- {t.title} (score: {t.score:.1f})")
    lines.append("\n## Defer to Tomorrow\n")
    for t in ranked_tasks[7:]:
        lines.append(f"- {t.title}")
    return "\n".join(lines)


async def reprioritize(
    current_ranked_tasks: list[RankedTask],
    new_task: Task,
) -> tuple[list[RankedTask], str]:
    INJECTION_BOOST = 1.30

    all_tasks = list(current_ranked_tasks) + [new_task]
    all_ranked = DeterministicScoringEngine.score_tasks(all_tasks)

    for rt in all_ranked:
        if rt.id == new_task.id:
            boosted = round(rt.score * INJECTION_BOOST, 1)
            rt.score = boosted
            rt.rationale = (
                f"Injected task: base score {rt.score:.1f} × {INJECTION_BOOST} boost = {boosted:.1f}. "
                f"Manual injection indicates urgency. "
                f"{rt.rationale}"
            )
            break

    all_ranked.sort(key=lambda t: t.score, reverse=True)
    for i, t in enumerate(all_ranked):
        t.rank = i + 1

    injected_rank = next(
        (i for i, t in enumerate(all_ranked) if t.id == new_task.id), -1
    )
    if injected_rank == 0:
        change_summary = f"New task '{new_task.title}' placed at #1 (score: {all_ranked[0].score:.1f})"
    elif injected_rank <= 3:
        change_summary = f"New task '{new_task.title}' entered top 3 at position #{injected_rank + 1}"
    else:
        change_summary = (
            f"New task '{new_task.title}' injected at position #{injected_rank + 1}"
        )

    return all_ranked, change_summary


def _build_ranked_list(tasks: list[RankedTask]) -> list[RankedTask]:
    return [
        RankedTask(
            **t.model_dump(exclude={"rank", "score", "rationale", "score_breakdown"}),
            rank=i + 1,
            score=t.score or 0.0,
            rationale=t.rationale or "",
            score_breakdown=t.score_breakdown or {},
        )
        for i, t in enumerate(tasks)
    ]


def build_daily_plan_from_tasks(
    tasks: list[RankedTask],
    alerts: list[Alert] | None = None,
) -> DailyPlan:
    if not tasks:
        return DailyPlan()

    ranked_list = _build_ranked_list(tasks)
    top3 = ranked_list[:3]
    do_next = ranked_list[3:6]
    blocked = [t for t in ranked_list if t.status == "blocked"]
    deferred = [t for t in ranked_list[6:] if t.status != "blocked"]

    return DailyPlan(
        generated_at=datetime.now(timezone.utc).isoformat(),
        top_priorities=top3,
        do_next=do_next,
        deferred=deferred,
        blocked=blocked,
        alerts=alerts or [],
        ranked_tasks=ranked_list,
    )
