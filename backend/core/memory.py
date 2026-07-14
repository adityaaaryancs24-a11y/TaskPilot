from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from core.state import _get_db, _ensure_db

logger = logging.getLogger(__name__)


class MemorySystem:
    @staticmethod
    def record_preference(
        key: str, value: str, source: str = "inferred", confidence: float = 0.5
    ):
        _ensure_db()
        conn = _get_db()
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """INSERT INTO user_preferences (preference_key, preference_value, source, confidence, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(preference_key) DO UPDATE SET
                 preference_value = excluded.preference_value,
                 source = CASE WHEN excluded.source = 'explicit' THEN 'explicit' ELSE user_preferences.source END,
                 confidence = excluded.confidence,
                 updated_at = excluded.updated_at""",
            (key, value, source, confidence, now),
        )
        conn.commit()
        conn.close()

    @staticmethod
    def get_preference(key: str) -> Optional[str]:
        _ensure_db()
        conn = _get_db()
        row = conn.execute(
            "SELECT preference_value FROM user_preferences WHERE preference_key = ?",
            (key,),
        ).fetchone()
        conn.close()
        return row["preference_value"] if row else None

    @staticmethod
    def get_all_preferences() -> dict[str, str]:
        _ensure_db()
        conn = _get_db()
        rows = conn.execute(
            "SELECT preference_key, preference_value FROM user_preferences"
        ).fetchall()
        conn.close()
        return {r["preference_key"]: r["preference_value"] for r in rows}

    @staticmethod
    def record_completion(
        task_id: str,
        task_title: str,
        source_type: str,
        priority: str | None,
        completed_at: str | None = None,
    ):
        _ensure_db()
        conn = _get_db()
        now = completed_at or datetime.now(timezone.utc).isoformat()
        dt = datetime.fromisoformat(now)
        conn.execute(
            """INSERT INTO completion_history
               (task_id, task_title, task_source_type, completed_at, completion_hour, day_of_week, task_priority)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (task_id, task_title, source_type, now, dt.hour, dt.weekday(), priority),
        )
        conn.commit()
        conn.close()

    @staticmethod
    def get_completion_patterns() -> dict[str, Any]:
        _ensure_db()
        conn = _get_db()
        rows = conn.execute("""
            SELECT completion_hour, day_of_week, COUNT(*) as count
            FROM completion_history
            GROUP BY completion_hour, day_of_week
            ORDER BY count DESC
            LIMIT 10
        """).fetchall()
        conn.close()

        patterns = []
        for r in rows:
            patterns.append(
                {
                    "hour": r["completion_hour"],
                    "day": r["day_of_week"],
                    "count": r["count"],
                }
            )
        return {"peak_completion_patterns": patterns}

    @staticmethod
    def get_preference_boosts() -> dict[str, float]:
        prefs = MemorySystem.get_all_preferences()
        boosts: dict[str, float] = {}
        for key, value in prefs.items():
            try:
                boosts[key] = float(value)
            except (ValueError, TypeError):
                pass
        return boosts

    @staticmethod
    def learn_from_feedback(task_id: str, action: str, preference: str):
        if preference and action:
            if action == "upvote":
                existing = MemorySystem.get_preference(preference)
                current = float(existing) if existing else 1.0
                MemorySystem.record_preference(
                    preference,
                    str(round(current * 1.05, 3)),
                    source="explicit",
                    confidence=0.7,
                )
            elif action == "downvote":
                existing = MemorySystem.get_preference(preference)
                current = float(existing) if existing else 1.0
                MemorySystem.record_preference(
                    preference,
                    str(round(current * 0.95, 3)),
                    source="explicit",
                    confidence=0.7,
                )

    @staticmethod
    def infer_preferences_from_tasks(tasks: list) -> None:
        source_counts: dict[str, int] = {}
        priority_counts: dict[str, int] = {}
        for t in tasks:
            source_type = getattr(t, "source_type", "") or ""
            priority = getattr(t, "priority", "") or ""
            if source_type:
                source_counts[source_type] = source_counts.get(source_type, 0) + 1
            if priority:
                priority_counts[priority] = priority_counts.get(priority, 0) + 1

        if source_counts:
            top_source = max(source_counts, key=source_counts.get)
            MemorySystem.record_preference(
                "preferred_source", top_source, source="inferred", confidence=0.4
            )
        if priority_counts:
            top_priority = max(priority_counts, key=priority_counts.get)
            MemorySystem.record_preference(
                "common_priority", top_priority, source="inferred", confidence=0.3
            )

    @staticmethod
    def detect_deferred_tasks(
        tasks: list, threshold_runs: int = 3
    ) -> list[dict[str, Any]]:
        _ensure_db()
        conn = _get_db()
        rows = conn.execute(
            """
            SELECT tasks_json FROM runs ORDER BY id DESC LIMIT ?
        """,
            (threshold_runs,),
        ).fetchall()
        conn.close()

        if len(rows) < threshold_runs:
            return []

        deferred: list[dict[str, Any]] = []
        task_appearances: dict[str, int] = {}
        task_details: dict[str, dict] = {}

        for row in rows:
            run_tasks = json.loads(row["tasks_json"])
            for t in run_tasks:
                tid = t.get("id", "")
                if tid:
                    task_appearances[tid] = task_appearances.get(tid, 0) + 1
                    if tid not in task_details:
                        task_details[tid] = {
                            "title": t.get("title", ""),
                            "priority": t.get("priority"),
                            "source_type": t.get("source_type"),
                        }

        for tid, count in task_appearances.items():
            if count == threshold_runs:
                details = task_details.get(tid, {})
                deferred.append(
                    {
                        "task_id": tid,
                        "title": details.get("title", ""),
                        "priority": details.get("priority"),
                        "source_type": details.get("source_type"),
                        "appeared_in_last_n_runs": count,
                        "reason": "Task has persisted across multiple pipeline runs without completion",
                    }
                )

        return deferred

    @staticmethod
    def record_agent_memory(agent_name: str, key: str, value: str):
        _ensure_db()
        conn = _get_db()
        now = datetime.now(timezone.utc).isoformat()
        existing = conn.execute(
            "SELECT id FROM agent_memory WHERE agent_name = ? AND memory_key = ?",
            (agent_name, key),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE agent_memory SET memory_value = ?, updated_at = ? WHERE agent_name = ? AND memory_key = ?",
                (value, now, agent_name, key),
            )
        else:
            conn.execute(
                "INSERT INTO agent_memory (agent_name, memory_key, memory_value, updated_at) VALUES (?, ?, ?, ?)",
                (agent_name, key, value, now),
            )
        conn.commit()
        conn.close()

    @staticmethod
    def get_agent_memory(agent_name: str, key: str) -> Optional[str]:
        _ensure_db()
        conn = _get_db()
        row = conn.execute(
            "SELECT memory_value FROM agent_memory WHERE agent_name = ? AND memory_key = ?",
            (agent_name, key),
        ).fetchone()
        conn.close()
        return row["memory_value"] if row else None


memory_system = MemorySystem()
