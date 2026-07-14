from datetime import datetime, timezone
from typing import Any

from core.state import store, _get_db
from core.connector_registry import connector_registry


def get_connector_status() -> list[dict[str, Any]]:
    return [
        {
            "name": c.name,
            "connected": c.connected,
            "last_sync": c.last_sync,
            "error": c.error,
        }
        for c in connector_registry.values()
    ]


def get_sync_latency() -> list[dict[str, Any]]:
    conn = _get_db()
    rows = conn.execute(
        "SELECT step_name, timestamp, duration_ms, status FROM traces "
        "WHERE step_name LIKE 'sync_%' ORDER BY id DESC LIMIT 50"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_ingestion_volume() -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    conn = _get_db()
    rows = conn.execute(
        "SELECT timestamp, tasks_json FROM runs ORDER BY id DESC LIMIT 20"
    ).fetchall()
    conn.close()
    volumes = []
    for r in rows:
        import json

        tasks = json.loads(r["tasks_json"])
        volumes.append(
            {
                "timestamp": r["timestamp"],
                "count": len(tasks),
            }
        )
    return volumes


def get_llm_usage() -> list[dict[str, Any]]:
    conn = _get_db()
    rows = conn.execute(
        "SELECT timestamp, step_name, duration_ms, tokens_used, status "
        "FROM traces WHERE tokens_used > 0 ORDER BY id DESC LIMIT 50"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_api_latency() -> dict[str, Any]:
    conn = _get_db()
    avg_row = conn.execute(
        "SELECT AVG(duration_ms) as avg_latency, COUNT(*) as total_calls "
        "FROM traces WHERE timestamp > datetime('now', '-1 hour')"
    ).fetchone()
    conn.close()
    return {
        "avg_latency_ms": round(avg_row["avg_latency"], 1)
        if avg_row and avg_row["avg_latency"]
        else 0,
        "total_calls": avg_row["total_calls"] if avg_row else 0,
    }


def get_websocket_health() -> dict[str, Any]:
    from core.websocket_manager import ws_manager

    total = sum(len(v) for v in ws_manager._connections.values())
    channels = {k: len(v) for k, v in ws_manager._connections.items()}
    return {
        "total_connections": total,
        "channels": channels,
    }


def get_metrics_summary() -> dict[str, Any]:
    return {
        "connectors": get_connector_status(),
        "sync_latency": get_sync_latency()[:10],
        "ingestion_volume": get_ingestion_volume()[:10],
        "llm_usage": get_llm_usage()[:10],
        "api_latency": get_api_latency(),
        "websocket_health": get_websocket_health(),
        "task_count": len(store.current_tasks),
        "has_plan": store.current_plan is not None,
    }
