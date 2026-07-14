from __future__ import annotations

import time
from typing import Callable

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    REGISTRY,
    CONTENT_TYPE_LATEST,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


# ── Counters ──
pipeline_runs_total = Counter(
    "taskpilot_pipeline_runs_total", "Total pipeline runs", ["status"]
)
pipeline_run_duration_seconds = Histogram(
    "taskpilot_pipeline_run_duration_seconds",
    "Pipeline run duration in seconds",
    buckets=[1, 5, 10, 30, 60, 120, 300],
)

llm_calls_total = Counter(
    "taskpilot_llm_calls_total", "Total LLM API calls", ["backend", "status"]
)
llm_latency_seconds = Histogram(
    "taskpilot_llm_latency_seconds",
    "LLM API call latency",
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30],
)

http_requests_total = Counter(
    "taskpilot_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
http_request_duration_seconds = Histogram(
    "taskpilot_http_request_duration_seconds",
    "HTTP request duration in seconds",
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5],
)

# ── Gauges ──
active_websocket_connections = Gauge(
    "taskpilot_active_ws_connections", "Active WebSocket connections"
)
task_count = Gauge("taskpilot_task_count", "Current number of tracked tasks")
extracted_task_count = Gauge(
    "taskpilot_extracted_task_count", "Count of LLM-extracted tasks"
)
dedup_groups = Gauge("taskpilot_dedup_groups", "Number of deduplication groups")

connector_status = Gauge(
    "taskpilot_connector_status", "Connector connectivity (1=connected)", ["connector"]
)

# ── Metrics middleware ──


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        endpoint = request.url.path
        start = time.monotonic()

        try:
            response = await call_next(request)
            status = str(response.status_code)
            http_request_duration_seconds.observe(time.monotonic() - start)
            http_requests_total.labels(
                method=method, endpoint=endpoint, status=status
            ).inc()
            return response
        except Exception:
            http_requests_total.labels(
                method=method, endpoint=endpoint, status="500"
            ).inc()
            raise


async def metrics_endpoint(request: Request) -> Response:
    return Response(content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
