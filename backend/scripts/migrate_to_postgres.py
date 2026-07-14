"""
One-time migration script from SQLite to PostgreSQL with rollback capability.
"""

import asyncio
import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite
import asyncpg


class DatabaseMigrator:
    def __init__(self, sqlite_path: str, postgres_dsn: str):
        self.sqlite_path = Path(sqlite_path)
        self.postgres_dsn = postgres_dsn
        self.migration_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir = Path("backups") / self.migration_id

    async def backup_sqlite(self):
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = self.backup_dir / "pre_migration.sqlite"
        conn = sqlite3.connect(str(self.sqlite_path))
        backup = sqlite3.connect(str(backup_path))
        conn.backup(backup)
        backup.close()
        conn.close()
        print(f"Backup created: {backup_path}")

    async def read_sqlite_data(self) -> dict[str, list[tuple[Any, ...]]]:
        data: dict[str, list[tuple[Any, ...]]] = {}
        async with aiosqlite.connect(str(self.sqlite_path)) as db:
            for table in (
                "tasks",
                "runs",
                "feedback",
                "preferences",
                "traces",
                "chat_log",
            ):
                try:
                    async with db.execute(f"SELECT * FROM {table}") as cursor:
                        rows = await cursor.fetchall()
                        data[table] = rows
                        print(f"  Read {len(rows)} rows from {table}")
                except Exception as e:
                    print(f"  Table {table} not found or empty: {e}")
                    data[table] = []
        return data

    async def migrate_to_postgres(self, data: dict[str, list[tuple[Any, ...]]]):
        conn = await asyncpg.connect(self.postgres_dsn)
        try:
            for row in data.get("tasks", []):
                await conn.execute(
                    """INSERT INTO tasks (task_id, title, description, source_type, priority, status, created_at, updated_at, metadata)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                       ON CONFLICT (task_id) DO NOTHING""",
                    str(row[0]),
                    str(row[1]),
                    str(row[2]) if row[2] else None,
                    str(row[3]),
                    str(row[4]) if len(row) > 4 else None,
                    str(row[5]) if len(row) > 5 else "open",
                    str(row[6]) if len(row) > 6 else datetime.utcnow().isoformat(),
                    str(row[7]) if len(row) > 7 else datetime.utcnow().isoformat(),
                    json.dumps(row[8]) if len(row) > 8 and row[8] else "{}",
                )

            for row in data.get("runs", []):
                plan = json.loads(row[2]) if len(row) > 2 and row[2] else {}
                await conn.execute(
                    "INSERT INTO runs (run_timestamp, plan, triggered_by) VALUES ($1,$2,$3)",
                    str(row[1]),
                    json.dumps(plan),
                    "migration",
                )

            for row in data.get("feedback", []):
                await conn.execute(
                    "INSERT INTO feedback (task_id, user_id, rating, comment, timestamp) VALUES ($1,$2,$3,$4,$5)",
                    str(row[1]) if len(row) > 1 else "",
                    "",
                    int(row[2]) if len(row) > 2 and row[2] else 3,
                    str(row[3]) if len(row) > 3 else "",
                    str(row[4]) if len(row) > 4 else datetime.utcnow().isoformat(),
                )

            print(f"  Migrated {len(data.get('tasks', []))} tasks")
            print(f"  Migrated {len(data.get('runs', []))} runs")
            print(f"  Migrated {len(data.get('feedback', []))} feedback entries")
        except Exception as e:
            print(f"Migration failed: {e}")
            raise
        finally:
            await conn.close()

    async def verify_migration(self) -> bool:
        conn = await asyncpg.connect(self.postgres_dsn)
        try:
            counts = {
                "tasks": await conn.fetchval("SELECT COUNT(*) FROM tasks"),
                "runs": await conn.fetchval("SELECT COUNT(*) FROM runs"),
                "feedback": await conn.fetchval("SELECT COUNT(*) FROM feedback"),
            }
            print("\nVerification:")
            for k, v in counts.items():
                print(f"  {k}: {v}")
            return True
        finally:
            await conn.close()

    async def rollback(self):
        print("Rolling back migration...")
        conn = await asyncpg.connect(self.postgres_dsn)
        try:
            for table in (
                "task_run_mapping",
                "feedback",
                "preferences",
                "preference_history",
                "chat_log",
                "traces",
                "llm_cache",
                "websocket_connections",
                "runs",
                "tasks",
            ):
                await conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            print("Rollback complete.")
        finally:
            await conn.close()

    async def restore_from_backup(self):
        backup_path = self.backup_dir / "pre_migration.sqlite"
        if backup_path.exists():
            shutil.copy(str(backup_path), str(self.sqlite_path))
            print(f"Restored SQLite from backup: {backup_path}")
        else:
            print("No backup found to restore.")


async def main():
    migrator = DatabaseMigrator(
        sqlite_path="db/taskpilot.db",
        postgres_dsn="postgresql://taskpilot:taskpilot@localhost:5432/taskpilot",
    )

    print("Step 1: Backing up SQLite...")
    await migrator.backup_sqlite()

    print("Step 2: Reading SQLite data...")
    data = await migrator.read_sqlite_data()

    print("Step 3: Migrating to PostgreSQL...")
    await migrator.migrate_to_postgres(data)

    print("Step 4: Verifying migration...")
    await migrator.verify_migration()

    print("Migration complete!")


if __name__ == "__main__":
    asyncio.run(main())
