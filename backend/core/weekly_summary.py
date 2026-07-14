from __future__ import annotations

import json
from typing import Any

from core.llm_client import call_llm

_SYSTEM = (
    "You are a technical writer producing a concise, standup-ready weekly "
    "summary for a software engineer. You receive daily plan records from "
    "the past week. Extract the signal: what was completed, what is still "
    "in flight, and what was blocked or deferred. "
    "Be specific — include task IDs and titles, not vague categories. "
    "No filler language. Under 300 words total. "
    "Output markdown only with exactly these three headers in order: "
    "'## Accomplished This Week', "
    "'## In Progress / Carried Over', "
    "'## Blockers & Deferred'."
)


def _compute_weekly_metrics(daily_plans: list[dict[str, Any]]) -> dict[str, Any]:
    total_tasks = set()
    done_tasks: set[str] = set()
    total_completed = 0
    all_blockers: list[str] = []

    for day in daily_plans:
        for t in day.get("top_3", []):
            tid = t.get("id")
            if tid:
                total_tasks.add(tid)
        for t in day.get("completed", []):
            tid = t.get("id")
            if tid:
                done_tasks.add(tid)
                total_completed += 1
        for t in day.get("blockers", []):
            tid = t.get("id")
            title = t.get("title", "")
            if tid:
                all_blockers.append(f"{tid}: {title}")

    return {
        "days_with_data": len(daily_plans),
        "total_unique_tasks": len(total_tasks),
        "total_completed_this_week": total_completed,
        "unique_completed_ids": list(done_tasks),
        "active_blockers": all_blockers,
    }


async def generate_weekly_summary(daily_plans: list[dict[str, Any]]) -> str:
    if not daily_plans:
        return (
            "## Accomplished This Week\n\n"
            "No plan history available.\n\n"
            "## In Progress / Carried Over\n\n"
            "—\n\n"
            "## Blockers & Deferred\n\n"
            "—"
        )

    metrics = _compute_weekly_metrics(daily_plans)

    user_prompt = (
        "Generate a weekly summary from these daily plan records.\n"
        "Follow your instructions exactly:\n"
        "- Use exactly three headers\n"
        "- Mention task IDs where possible\n"
        "- Stay under 300 words\n\n"
        f"WEEKLY METRICS:\n{json.dumps(metrics, indent=2)}\n\n"
        f"DAILY PLANS:\n{json.dumps(daily_plans, indent=2)}"
    )

    try:
        response = await call_llm(
            prompt=user_prompt,
            system=_SYSTEM,
            json_mode=False,
            temperature=0.3,
            max_output_tokens=1024,
        )
        summary = response.text.strip()
        if not summary:
            return (
                "## Accomplished This Week\n\n"
                f"**{metrics['total_completed_this_week']}** task(s) completed across "
                f"{metrics['days_with_data']} day(s) with data.\n\n"
                "## In Progress / Carried Over\n\n"
                f"**{metrics['total_unique_tasks']}** unique task(s) tracked.\n\n"
                "## Blockers & Deferred\n\n"
                + (
                    f"{len(metrics['active_blockers'])} blocker(s):\n"
                    + "\n".join(f"- {b}" for b in metrics["active_blockers"])
                    if metrics["active_blockers"]
                    else "No blockers recorded."
                )
            )
        return summary
    except Exception:
        return (
            "## Accomplished This Week\n\n"
            f"**{metrics['total_completed_this_week']}** task(s) completed.\n\n"
            "## In Progress / Carried Over\n\n"
            f"**{metrics['total_unique_tasks']}** unique task(s) tracked.\n\n"
            "## Blockers & Deferred\n\n"
            + (
                f"{len(metrics['active_blockers'])} blocker(s):\n"
                + "\n".join(f"- {b}" for b in metrics["active_blockers"])
                if metrics["active_blockers"]
                else "No blockers recorded."
            )
        )
