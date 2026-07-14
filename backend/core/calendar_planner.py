from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from core.state import _get_db, _ensure_db
from models.task import RankedTask

logger = logging.getLogger(__name__)


class CalendarPlanner:
    @staticmethod
    def seed_simulated_events(days_ahead: int = 7):
        _ensure_db()
        conn = _get_db()
        now = datetime.now(timezone.utc)
        base = now.replace(hour=9, minute=0, second=0, microsecond=0)

        events = [
            {
                "event_id": "standup_today",
                "title": "Daily Standup",
                "start": base.isoformat(),
                "end": (base + timedelta(minutes=15)).isoformat(),
                "is_all_day": 0,
                "source": "simulated",
            },
            {
                "event_id": "sprint_planning",
                "title": "Sprint Planning",
                "start": (now + timedelta(days=1))
                .replace(hour=10, minute=0)
                .isoformat(),
                "end": (now + timedelta(days=1)).replace(hour=11, minute=0).isoformat(),
                "is_all_day": 0,
                "source": "simulated",
            },
            {
                "event_id": "lunch_break",
                "title": "Lunch",
                "start": base.replace(hour=12, minute=0).isoformat(),
                "end": base.replace(hour=13, minute=0).isoformat(),
                "is_all_day": 0,
                "source": "simulated",
            },
            {
                "event_id": "weekly_sync",
                "title": "Weekly Team Sync",
                "start": (now + timedelta(days=2))
                .replace(hour=14, minute=0)
                .isoformat(),
                "end": (now + timedelta(days=2))
                .replace(hour=14, minute=30)
                .isoformat(),
                "is_all_day": 0,
                "source": "simulated",
            },
            {
                "event_id": "friday_demo",
                "title": "Stakeholder Demo",
                "start": (now + timedelta(days=(4 - now.weekday()) % 7))
                .replace(hour=14, minute=0)
                .isoformat(),
                "end": (now + timedelta(days=(4 - now.weekday()) % 7))
                .replace(hour=15, minute=0)
                .isoformat(),
                "is_all_day": 0,
                "source": "simulated",
            },
            {
                "event_id": "customer_demo_prep",
                "title": "Customer Demo Walkthrough Prep",
                "start": (now + timedelta(days=1))
                .replace(hour=9, minute=0)
                .isoformat(),
                "end": (now + timedelta(days=1)).replace(hour=9, minute=45).isoformat(),
                "is_all_day": 0,
                "source": "simulated",
            },
            {
                "event_id": "lunch_friday",
                "title": "Team Lunch",
                "start": (now + timedelta(days=(4 - now.weekday()) % 7))
                .replace(hour=13, minute=0)
                .isoformat(),
                "end": (now + timedelta(days=(4 - now.weekday()) % 7))
                .replace(hour=14, minute=0)
                .isoformat(),
                "is_all_day": 0,
                "source": "simulated",
            },
            {
                "event_id": "design_review",
                "title": "Design Review: Onboarding Flow",
                "start": (now + timedelta(days=2))
                .replace(hour=11, minute=0)
                .isoformat(),
                "end": (now + timedelta(days=2))
                .replace(hour=11, minute=30)
                .isoformat(),
                "is_all_day": 0,
                "source": "simulated",
            },
            {
                "event_id": "weekly_sync_pm",
                "title": "1:1 with PM",
                "start": (now + timedelta(days=1))
                .replace(hour=15, minute=0)
                .isoformat(),
                "end": (now + timedelta(days=1))
                .replace(hour=15, minute=30)
                .isoformat(),
                "is_all_day": 0,
                "source": "simulated",
            },
            {
                "event_id": "sprint_retro",
                "title": "Sprint Retrospective",
                "start": (now + timedelta(days=3))
                .replace(hour=10, minute=0)
                .isoformat(),
                "end": (now + timedelta(days=3)).replace(hour=11, minute=0).isoformat(),
                "is_all_day": 0,
                "source": "simulated",
            },
        ]

        for ev in events:
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO calendar_events (event_id, title, start_time, end_time, is_all_day, source)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        ev["event_id"],
                        ev["title"],
                        ev["start"],
                        ev["end"],
                        ev["is_all_day"],
                        ev["source"],
                    ),
                )
            except Exception as e:
                logger.warning("Failed to seed event %s: %s", ev["event_id"], e)
        conn.commit()
        conn.close()

    @staticmethod
    def get_todays_events() -> list[dict[str, Any]]:
        _ensure_db()
        conn = _get_db()
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        today_end = now.replace(
            hour=23, minute=59, second=59, microsecond=999999
        ).isoformat()
        rows = conn.execute(
            "SELECT * FROM calendar_events WHERE start_time >= ? AND start_time <= ? ORDER BY start_time ASC",
            (today_start, today_end),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_events_for_date(date_str: str) -> list[dict[str, Any]]:
        _ensure_db()
        conn = _get_db()
        try:
            dt = datetime.fromisoformat(date_str)
        except (ValueError, TypeError):
            dt = datetime.now(timezone.utc)
        day_start = dt.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        day_end = dt.replace(
            hour=23, minute=59, second=59, microsecond=999999
        ).isoformat()
        rows = conn.execute(
            "SELECT * FROM calendar_events WHERE start_time >= ? AND start_time <= ? ORDER BY start_time ASC",
            (day_start, day_end),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_unavailable_slots(date_str: str | None = None) -> list[dict[str, Any]]:
        events = (
            CalendarPlanner.get_todays_events()
            if date_str is None
            else CalendarPlanner.get_events_for_date(date_str)
        )
        slots = []
        for ev in events:
            if not ev["is_all_day"]:
                slots.append(
                    {
                        "start": ev["start_time"],
                        "end": ev["end_time"],
                        "title": ev["title"],
                        "event_id": ev["event_id"],
                    }
                )
        return slots

    @staticmethod
    def generate_time_blocked_plan(
        ranked_tasks: list[RankedTask], date_str: str | None = None
    ) -> list[dict[str, Any]]:
        events = (
            CalendarPlanner.get_todays_events()
            if date_str is None
            else CalendarPlanner.get_events_for_date(date_str)
        )
        unavailable = [
            {"start": ev["start_time"], "end": ev["end_time"], "title": ev["title"]}
            for ev in events
            if not ev["is_all_day"]
        ]

        now = datetime.now(timezone.utc)
        if date_str:
            try:
                now = datetime.fromisoformat(date_str)
            except (ValueError, TypeError):
                pass

        day_start = now.replace(hour=9, minute=0, second=0, microsecond=0)
        lunch_start = now.replace(hour=12, minute=0, second=0, microsecond=0)
        lunch_end = now.replace(hour=13, minute=0, second=0, microsecond=0)
        day_end = now.replace(hour=18, minute=0, second=0, microsecond=0)

        available_slots = CalendarPlanner._compute_available_slots(
            day_start, day_end, unavailable
        )

        time_blocked = []
        task_idx = 0
        for slot_start, slot_end in available_slots:
            if task_idx >= len(ranked_tasks):
                break

            slot_minutes = (slot_end - slot_start).total_seconds() / 60
            if slot_minutes < 15:
                continue

            task_duration = min(60, slot_minutes)
            if task_duration < 15:
                task_duration = slot_minutes

            task = ranked_tasks[task_idx]
            time_blocked.append(
                {
                    "start": slot_start.isoformat(),
                    "end": (slot_start + timedelta(minutes=task_duration)).isoformat(),
                    "task_id": task.id,
                    "title": task.title,
                    "priority": task.priority,
                    "score": task.score,
                    "slot_type": "deep_work" if task_duration >= 45 else "quick_task",
                }
            )
            task_idx += 1

        context_switching_tasks = []
        while task_idx < len(ranked_tasks):
            context_switching_tasks.append(ranked_tasks[task_idx].id)
            task_idx += 1

        return {
            "time_blocks": time_blocked,
            "unavailable_slots": unavailable,
            "remaining_task_ids": context_switching_tasks,
            "date": (date_str or now.isoformat()),
        }

    @staticmethod
    def _compute_available_slots(
        day_start: datetime, day_end: datetime, unavailable: list[dict[str, Any]]
    ) -> list[tuple[datetime, datetime]]:
        busy_intervals = []
        for slot in unavailable:
            try:
                s = datetime.fromisoformat(slot["start"])
                e = datetime.fromisoformat(slot["end"])
                if s < day_end and e > day_start:
                    busy_intervals.append((max(s, day_start), min(e, day_end)))
            except (ValueError, TypeError):
                pass

        busy_intervals.sort()

        available = []
        current = day_start
        for b_start, b_end in busy_intervals:
            if current < b_start:
                available.append((current, b_start))
            current = max(current, b_end)
        if current < day_end:
            available.append((current, day_end))

        return available
