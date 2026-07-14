from __future__ import annotations

import logging
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from core.database import (
    save_state as db_save_state,
    load_state as db_load_state,
    save_trace as db_save_trace,
    save_chat_log as db_save_chat_log,
    save_feedback as db_save_feedback,
    get_user_preference_boosts as db_get_user_preference_boosts,
    get_daily_snapshots as db_get_daily_snapshots,
    get_team_velocity as db_get_team_velocity,
    get_recent_traces as db_get_recent_traces,
)
from models.task import Task, DailyPlan

logger = logging.getLogger(__name__)

# ── Synchronous SQLite fallback (kept for backward compat) ──

DB_DIR = Path(__file__).resolve().parent.parent / "db"
DB_PATH = str(DB_DIR / "taskpilot.db")
SCHEMA_PATH = str(DB_DIR / "schema.sql")


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = _get_db()
    conn.executescript(open(SCHEMA_PATH).read())
    conn.commit()
    conn.close()


def _ensure_db():
    if not DB_DIR.exists() or not Path(DB_PATH).exists():
        init_db()


# ── State Store ──


class StateStore:
    def __init__(self):
        self._lock = threading.Lock()
        self.current_tasks: list[Task] = []
        self.current_plan: Optional[DailyPlan] = None
        self.chat_history: list[dict] = []
        self.last_run_timestamp: Optional[str] = None
        self.narrative_alert: Optional[str] = None
        self.time_blocked_plan: Optional[list] = None
        self.highest_leverage_tasks: Optional[list] = None
        self.deferred_tasks: Optional[list] = None
        self._startup_time = datetime.now(timezone.utc)

    def update(self, tasks: list[Task], plan: Optional[DailyPlan] = None):
        with self._lock:
            self.current_tasks = tasks
            self.current_plan = plan
            self.last_run_timestamp = datetime.now(timezone.utc).isoformat()

    def add_chat_entry(self, question: str, answer: str, referenced_ids: list[str]):
        with self._lock:
            entry = {
                "question": question,
                "answer": answer,
                "referenced_task_ids": referenced_ids,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self.chat_history.append(entry)

    def get_state_summary(self) -> dict:
        with self._lock:
            return {
                "task_count": len(self.current_tasks),
                "has_plan": self.current_plan is not None,
                "chat_history_count": len(self.chat_history),
                "last_run": self.last_run_timestamp,
            }


store = StateStore()


# ── Async wrappers (delegate to core.database) ──


async def save_state(
    tasks: list[Task], plan: Optional[DailyPlan] = None, status: str = "ok"
):
    try:
        await db_save_state(tasks, plan, status)
    except Exception as e:
        logger.warning("Failed to save state async: %s", e)
        # Fall back to sync
        _save_state_sync(tasks, plan, status)


async def load_state() -> tuple[list[Task], Optional[DailyPlan]]:
    try:
        return await db_load_state()
    except Exception:
        pass
    try:
        return _load_state_sync()
    except Exception:
        return [], None


async def save_trace(
    step_name: str, duration_ms: float, tokens_used: int = 0, status: str = "ok"
):
    try:
        await db_save_trace(step_name, duration_ms, tokens_used, status)
    except Exception:
        _save_trace_sync(step_name, duration_ms, tokens_used, status)


async def save_chat_log(question: str, answer: str, referenced_ids: list[str]):
    try:
        await db_save_chat_log(question, answer, referenced_ids)
    except Exception:
        _save_chat_log_sync(question, answer, referenced_ids)


async def save_feedback(task_id: str, action: str, preference: str):
    try:
        await db_save_feedback(task_id, action, preference)
    except Exception:
        _save_feedback_sync(task_id, action, preference)


async def get_user_preference_boosts() -> dict[str, float]:
    try:
        return await db_get_user_preference_boosts()
    except Exception:
        return _get_user_preference_boosts_sync()


async def get_daily_snapshots(days: int = 7) -> list[dict[str, Any]]:
    try:
        return await db_get_daily_snapshots(days)
    except Exception:
        return _get_daily_snapshots_sync(days)


async def get_team_velocity(days: int = 7) -> dict[str, Any]:
    try:
        return await db_get_team_velocity(days)
    except Exception:
        return _get_team_velocity_sync(days)


async def get_recent_traces(limit: int = 50) -> list[dict]:
    try:
        return await db_get_recent_traces(limit)
    except Exception:
        return _get_recent_traces_sync(limit)


# ── Sync fallback implementations ──


def _save_state_sync(
    tasks: list[Task], plan: Optional[DailyPlan] = None, status: str = "ok"
):
    import json

    _ensure_db()
    conn = _get_db()
    tasks_json = json.dumps([t.model_dump(mode="json") for t in tasks], default=str)
    plan_json = json.dumps(plan.model_dump(mode="json"), default=str) if plan else None
    conn.execute(
        "INSERT INTO runs (timestamp, tasks_json, plan_json, pipeline_status) VALUES (?, ?, ?, ?)",
        (datetime.now(timezone.utc).isoformat(), tasks_json, plan_json, status),
    )
    conn.commit()
    conn.close()


def _load_state_sync() -> tuple[list[Task], Optional[DailyPlan]]:
    import json

    _ensure_db()
    conn = _get_db()
    row = conn.execute(
        "SELECT tasks_json, plan_json FROM runs ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if row is None:
        return [], None
    tasks = [Task(**t) for t in json.loads(row["tasks_json"])]
    plan = DailyPlan(**json.loads(row["plan_json"])) if row["plan_json"] else None
    return tasks, plan


def _save_trace_sync(
    step_name: str, duration_ms: float, tokens_used: int = 0, status: str = "ok"
):
    try:
        _ensure_db()
        conn = _get_db()
        conn.execute(
            "INSERT INTO traces (timestamp, step_name, duration_ms, tokens_used, status) VALUES (?, ?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(),
                step_name,
                duration_ms,
                tokens_used,
                status,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.debug("Failed to save trace sync: %s", e)


def _get_recent_traces_sync(limit: int = 50) -> list[dict]:
    try:
        _ensure_db()
        conn = _get_db()
        rows = conn.execute(
            "SELECT * FROM traces ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def _save_chat_log_sync(question: str, answer: str, referenced_ids: list[str]):
    _ensure_db()
    conn = _get_db()
    conn.execute(
        "INSERT INTO chat_log (timestamp, question, answer, referenced_task_ids) VALUES (?, ?, ?, ?)",
        (
            datetime.now(timezone.utc).isoformat(),
            question,
            answer,
            ",".join(referenced_ids),
        ),
    )
    conn.commit()
    conn.close()


def _save_feedback_sync(task_id: str, action: str, preference: str):
    _ensure_db()
    conn = _get_db()
    conn.execute(
        "INSERT INTO user_feedback (task_id, action, user_preference, timestamp) VALUES (?, ?, ?, datetime('now'))",
        (task_id, action, preference),
    )
    conn.commit()
    conn.close()


def _get_user_preference_boosts_sync() -> dict[str, float]:
    _ensure_db()
    conn = _get_db()
    rows = conn.execute("""
        SELECT user_preference,
               SUM(CASE WHEN action = 'upvote' THEN 1 WHEN action = 'downvote' THEN -1 ELSE 0 END) as net
        FROM user_feedback
        GROUP BY user_preference
        HAVING net > 0
        ORDER BY net DESC
    """).fetchall()
    conn.close()
    boosts: dict[str, float] = {}
    for row in rows:
        pref = row["user_preference"]
        net = row["net"]
        multiplier = 1.0 + min(net, 5) * 0.04
        boosts[pref] = round(multiplier, 3)
    return boosts


def _get_daily_snapshots_sync(days: int = 7) -> list[dict[str, Any]]:
    import json

    _ensure_db()
    conn = _get_db()
    rows = conn.execute(
        """
        SELECT date(timestamp) as day,
               MAX(timestamp) as last_run_ts,
               tasks_json,
               plan_json
        FROM runs
        WHERE timestamp >= date('now', '-' || ? || ' days')
        GROUP BY date(timestamp)
        ORDER BY day ASC
    """,
        (days,),
    ).fetchall()
    conn.close()

    if not rows:
        return []

    daily_plans: list[dict] = []
    prev_tasks: list[dict] = []

    for row in rows:
        tasks: list[dict] = json.loads(row["tasks_json"])
        plan: dict | None = json.loads(row["plan_json"]) if row["plan_json"] else None

        curr_done_ids = {t["id"] for t in tasks if t.get("status") == "done"}
        prev_done_ids = {t["id"] for t in prev_tasks if t.get("status") == "done"}
        newly_completed = [
            {"id": t["id"], "title": t.get("title", "")}
            for t in tasks
            if t.get("status") == "done" and t["id"] not in prev_done_ids
        ]

        daily: dict[str, Any] = {
            "date": row["day"],
            "top_3": [],
            "completed": newly_completed,
            "deferred": [],
            "blockers": [],
            "task_count": len(tasks),
            "done_count": len(curr_done_ids),
        }

        if plan:
            daily["top_3"] = [
                {"id": t.get("id"), "title": t.get("title"), "status": t.get("status")}
                for t in plan.get("top_priorities", [])
            ]
            daily["deferred"] = [
                {"id": t.get("id"), "title": t.get("title")}
                for t in plan.get("deferred", [])
            ]

        daily["blockers"] = [
            {"id": t["id"], "title": t.get("title", ""), "blocked_by": ""}
            for t in tasks
            if t.get("status") == "blocked"
        ]

        daily_plans.append(daily)
        prev_tasks = tasks

    return daily_plans


def _get_team_velocity_sync(days: int = 7) -> dict[str, Any]:
    import json

    _ensure_db()
    conn = _get_db()
    rows = conn.execute(
        """
        SELECT date(timestamp) as day,
               tasks_json
        FROM runs
        WHERE timestamp >= date('now', '-' || ? || ' days')
        GROUP BY date(timestamp)
        ORDER BY day ASC
    """,
        (days,),
    ).fetchall()
    conn.close()

    daily_counts = []
    for row in rows:
        tasks = json.loads(row["tasks_json"])
        done = sum(1 for t in tasks if t.get("status") == "done")
        daily_counts.append({"day": row["day"], "completed": done, "total": len(tasks)})

    return {"daily_counts": daily_counts}
