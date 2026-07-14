from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text
from sqlalchemy.pool import NullPool

from core.config import settings

logger = logging.getLogger(__name__)

DB_DIR = Path(__file__).resolve().parent.parent / "db"
SCHEMA_PATH = str(DB_DIR / "schema.sql")

engine = None
AsyncSessionLocal = None


async def get_db() -> AsyncSession:
    global AsyncSessionLocal
    if AsyncSessionLocal is None:
        await init_db()
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_engine():
    global engine, AsyncSessionLocal
    url = settings.database_url
    connect_args = {}
    if "sqlite" in url:
        connect_args["check_same_thread"] = False
    engine = create_async_engine(
        url, echo=False, poolclass=NullPool, connect_args=connect_args
    )
    AsyncSessionLocal = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    logger.info("Database engine created: %s", url.split("://")[0])
    return engine


async def init_db():
    global engine, AsyncSessionLocal
    if engine is None:
        await create_engine()

    async with AsyncSessionLocal() as session:
        if "sqlite" in settings.database_url:
            DB_DIR.mkdir(parents=True, exist_ok=True)
            with open(SCHEMA_PATH) as f:
                schema_sql = f.read()
            for statement in schema_sql.split(";"):
                stmt = statement.strip()
                if stmt:
                    await session.execute(text(stmt))
        else:
            await session.execute(
                text("""
                CREATE TABLE IF NOT EXISTS runs (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    tasks_json JSONB,
                    plan_json JSONB,
                    pipeline_status TEXT DEFAULT 'ok'
                );
                CREATE TABLE IF NOT EXISTS chat_log (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    question TEXT,
                    answer TEXT,
                    referenced_task_ids TEXT
                );
                CREATE TABLE IF NOT EXISTS traces (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    step_name TEXT,
                    duration_ms FLOAT,
                    tokens_used INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'ok'
                );
                CREATE TABLE IF NOT EXISTS user_feedback (
                    id SERIAL PRIMARY KEY,
                    task_id TEXT,
                    action TEXT,
                    user_preference TEXT,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id SERIAL PRIMARY KEY,
                    preference_key TEXT UNIQUE,
                    preference_value TEXT,
                    source TEXT DEFAULT 'inferred',
                    confidence FLOAT DEFAULT 0.5,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS completion_history (
                    id SERIAL PRIMARY KEY,
                    task_id TEXT,
                    task_title TEXT,
                    task_source_type TEXT,
                    completed_at TIMESTAMPTZ,
                    completion_hour INTEGER,
                    day_of_week INTEGER,
                    task_priority TEXT
                );
                CREATE TABLE IF NOT EXISTS agent_memory (
                    id SERIAL PRIMARY KEY,
                    agent_name TEXT,
                    memory_key TEXT,
                    memory_value TEXT,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE(agent_name, memory_key)
                );
            """)
            )
        await session.commit()

    logger.info("Database initialized")


async def close_db():
    global engine
    if engine:
        await engine.dispose()
        logger.info("Database engine disposed")


async def save_state(tasks: list, plan=None, status="ok"):
    global AsyncSessionLocal
    if AsyncSessionLocal is None:
        raise RuntimeError("Database not initialized (AsyncSessionLocal is None)")

    async with AsyncSessionLocal() as session:
        tasks_json = json.dumps([t.model_dump(mode="json") for t in tasks], default=str)
        plan_json = (
            json.dumps(plan.model_dump(mode="json"), default=str) if plan else None
        )
        if "sqlite" in settings.database_url:
            await session.execute(
                text(
                    "INSERT INTO runs (timestamp, tasks_json, plan_json, pipeline_status) VALUES (:ts, :tj, :pj, :ps)"
                ),
                {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "tj": tasks_json,
                    "pj": plan_json,
                    "ps": status,
                },
            )
        else:
            await session.execute(
                text(
                    "INSERT INTO runs (tasks_json, plan_json, pipeline_status) VALUES (:tj, :pj, :ps)"
                ),
                {"tj": tasks_json, "pj": plan_json, "ps": status},
            )
        await session.commit()


async def load_state():
    from models.task import Task, DailyPlan

    async with AsyncSessionLocal() as session:
        if "sqlite" in settings.database_url:
            row = (
                await session.execute(
                    text(
                        "SELECT tasks_json, plan_json FROM runs ORDER BY id DESC LIMIT 1"
                    )
                )
            ).fetchone()
        else:
            row = (
                await session.execute(
                    text(
                        "SELECT tasks_json::TEXT as tasks_json, plan_json::TEXT as plan_json FROM runs ORDER BY id DESC LIMIT 1"
                    )
                )
            ).fetchone()

    if row is None:
        return [], None
    tasks = [Task(**t) for t in json.loads(row[0])]
    plan = DailyPlan(**json.loads(row[1])) if row[1] else None
    return tasks, plan


async def save_trace(
    step_name: str, duration_ms: float, tokens_used: int = 0, status: str = "ok"
):
    global AsyncSessionLocal
    if AsyncSessionLocal is None:
        raise RuntimeError("Database not initialized (AsyncSessionLocal is None)")
    async with AsyncSessionLocal() as session:
        ts = datetime.now(timezone.utc).isoformat()
        if "sqlite" in settings.database_url:
            await session.execute(
                text(
                    "INSERT INTO traces (timestamp, step_name, duration_ms, tokens_used, status) VALUES (:ts, :sn, :dm, :tu, :st)"
                ),
                {
                    "ts": ts,
                    "sn": step_name,
                    "dm": duration_ms,
                    "tu": tokens_used,
                    "st": status,
                },
            )
        else:
            await session.execute(
                text(
                    "INSERT INTO traces (step_name, duration_ms, tokens_used, status) VALUES (:sn, :dm, :tu, :st)"
                ),
                {"sn": step_name, "dm": duration_ms, "tu": tokens_used, "st": status},
            )
        await session.commit()


async def get_recent_traces(limit: int = 50) -> list[dict]:
    try:
        async with AsyncSessionLocal() as session:
            rows = (
                await session.execute(
                    text("SELECT * FROM traces ORDER BY id DESC LIMIT :lim"),
                    {"lim": limit},
                )
            ).fetchall()
            return [dict(r._mapping) for r in rows]
    except Exception:
        return []


async def save_chat_log(question: str, answer: str, referenced_ids: list[str]):
    async with AsyncSessionLocal() as session:
        ts = datetime.now(timezone.utc).isoformat()
        if "sqlite" in settings.database_url:
            await session.execute(
                text(
                    "INSERT INTO chat_log (timestamp, question, answer, referenced_task_ids) VALUES (:ts, :q, :a, :rid)"
                ),
                {"ts": ts, "q": question, "a": answer, "rid": ",".join(referenced_ids)},
            )
        else:
            await session.execute(
                text(
                    "INSERT INTO chat_log (question, answer, referenced_task_ids) VALUES (:q, :a, :rid)"
                ),
                {"q": question, "a": answer, "rid": ",".join(referenced_ids)},
            )
        await session.commit()


async def save_feedback(task_id: str, action: str, preference: str):
    async with AsyncSessionLocal() as session:
        if "sqlite" in settings.database_url:
            await session.execute(
                text(
                    "INSERT INTO user_feedback (task_id, action, user_preference, timestamp) VALUES (:tid, :act, :pref, datetime('now'))"
                ),
                {"tid": task_id, "act": action, "pref": preference},
            )
        else:
            await session.execute(
                text(
                    "INSERT INTO user_feedback (task_id, action, user_preference) VALUES (:tid, :act, :pref)"
                ),
                {"tid": task_id, "act": action, "pref": preference},
            )
        await session.commit()


async def get_user_preference_boosts() -> dict[str, float]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
            SELECT user_preference,
                   SUM(CASE WHEN action = 'upvote' THEN 1 WHEN action = 'downvote' THEN -1 ELSE 0 END) as net
            FROM user_feedback
            GROUP BY user_preference
            HAVING net > 0
            ORDER BY net DESC
        """)
        )
        rows = result.fetchall()
    boosts: dict[str, float] = {}
    for row in rows:
        pref = row[0]
        net = row[1]
        multiplier = 1.0 + min(net, 5) * 0.04
        boosts[pref] = round(multiplier, 3)
    return boosts


async def get_daily_snapshots(days: int = 7) -> list[dict[str, Any]]:

    async with AsyncSessionLocal() as session:
        if "sqlite" in settings.database_url:
            rows = (
                await session.execute(
                    text("""
                SELECT date(timestamp) as day,
                       MAX(timestamp) as last_run_ts,
                       tasks_json,
                       plan_json
                FROM runs
                WHERE timestamp >= date('now', '-' || :days || ' days')
                GROUP BY date(timestamp)
                ORDER BY day ASC
            """),
                    {"days": days},
                )
            ).fetchall()
        else:
            rows = (
                await session.execute(
                    text("""
                SELECT date(timestamp) as day,
                       MAX(timestamp) as last_run_ts,
                       tasks_json::TEXT as tasks_json,
                       plan_json::TEXT as plan_json
                FROM runs
                WHERE timestamp >= NOW() - (:days || ' days')::INTERVAL
                GROUP BY date(timestamp)
                ORDER BY day ASC
            """),
                    {"days": str(days)},
                )
            ).fetchall()

    if not rows:
        return []

    daily_plans: list[dict] = []
    prev_tasks: list[dict] = []

    for row in rows:
        tasks: list[dict] = json.loads(row[2])
        plan: dict | None = json.loads(row[3]) if row[3] else None

        curr_done_ids = {t["id"] for t in tasks if t.get("status") == "done"}
        prev_done_ids = {t["id"] for t in prev_tasks if t.get("status") == "done"}
        newly_completed = [
            {"id": t["id"], "title": t.get("title", "")}
            for t in tasks
            if t.get("status") == "done" and t["id"] not in prev_done_ids
        ]

        daily: dict[str, Any] = {
            "date": row[0],
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


async def get_team_velocity(days: int = 7) -> dict[str, Any]:
    async with AsyncSessionLocal() as session:
        if "sqlite" in settings.database_url:
            rows = (
                await session.execute(
                    text("""
                SELECT date(timestamp) as day, tasks_json
                FROM runs
                WHERE timestamp >= date('now', '-' || :days || ' days')
                GROUP BY date(timestamp)
                ORDER BY day ASC
            """),
                    {"days": days},
                )
            ).fetchall()
        else:
            rows = (
                await session.execute(
                    text("""
                SELECT date(timestamp) as day, tasks_json::TEXT as tasks_json
                FROM runs
                WHERE timestamp >= NOW() - (:days || ' days')::INTERVAL
                GROUP BY date(timestamp)
                ORDER BY day ASC
            """),
                    {"days": str(days)},
                )
            ).fetchall()

    daily_counts = []
    for row in rows:
        tasks = json.loads(row[1])
        done = sum(1 for t in tasks if t.get("status") == "done")
        daily_counts.append({"day": row[0], "completed": done, "total": len(tasks)})

    return {"daily_counts": daily_counts}
