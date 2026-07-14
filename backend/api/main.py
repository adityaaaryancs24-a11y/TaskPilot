from __future__ import annotations

import logging
import os
from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv

dotenv_path = Path(__file__).resolve().parent.parent / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)
else:
    load_dotenv()

if not os.environ.get("LLM_API_KEY") and os.environ.get("XAI_API_KEY"):
    os.environ["LLM_API_KEY"] = os.environ["XAI_API_KEY"]

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from core.config import settings
from core.structured_logging import setup_logging
from core.prometheus_metrics import PrometheusMiddleware, metrics_endpoint, task_count

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("TaskPilot AI starting up...")

    from core.database import init_db, close_db, load_state
    from core import state
    from core.state import store
    from core.sync_engine import sync_engine
    from core.embedding_model import load_embedding_model

    try:
        await init_db()
    except Exception:
        logger.warning("Async DB init failed, using sync fallback")
        state.init_db()

    try:
        tasks, plan = await load_state()
    except Exception:
        logger.warning("Async load_state failed, using in-memory store")
        tasks, plan = [], None
    if tasks:
        store.update(tasks, plan)
        task_count.set(len(tasks))
        logger.info("Restored %d tasks from database", len(tasks))

    # Load embedding model in background
    try:
        import asyncio

        asyncio.create_task(asyncio.to_thread(load_embedding_model))
    except Exception:
        pass

    await _validate_connectors()

    try:
        from core.agent import run_pipeline

        await run_pipeline()
        logger.info("Initial pipeline run complete")
    except Exception as e:
        logger.error("Initial pipeline run failed: %s", e)
        logger.error("Call GET /api/refresh to retry")

    await sync_engine.start()
    logger.info("Sync engine started")

    from core.monitor_service import monitor_service

    await monitor_service.start()
    logger.info("Monitor service started")

    yield

    logger.info("TaskPilot AI shutting down...")
    from core.monitor_service import monitor_service

    await monitor_service.stop()
    await sync_engine.stop()
    await close_db()
    logger.info("Shutdown complete")


app = FastAPI(
    title="TaskPilot AI",
    description="Production-grade agentic task prioritization platform.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Production middleware stack
if settings.prometheus_enabled:
    app.add_middleware(PrometheusMiddleware)

from core.rate_limiter import RateLimitMiddleware

app.add_middleware(RateLimitMiddleware)

app.include_router(router)


# Prometheus metrics endpoint
@app.get("/metrics")
async def metrics():
    return await metrics_endpoint(None)


def _mask(s: str | None) -> str:
    if not s:
        return ""
    if len(s) <= 8:
        return s[:2] + "***"
    return s[:4] + "****" + s[-4:]


async def _validate_connectors():
    from core.connector_registry import connector_registry
    from core.prometheus_metrics import connector_status

    results = {}
    for name, connector in connector_registry.items():
        try:
            ok = await connector.connect()
            results[name] = {"connected": ok, "error": connector.error}
            connector_status.labels(connector=name).set(1 if ok else 0)
            if ok:
                logger.info("Connector %s — connected", connector.name)
            else:
                logger.warning(
                    "Connector %s — %s",
                    connector.name,
                    connector.error or "unknown error",
                )
        except Exception as e:
            results[name] = {"connected": False, "error": str(e)}
            connector_status.labels(connector=name).set(0)
            logger.error("Connector %s — failed: %s", connector.name, e)
    return results
