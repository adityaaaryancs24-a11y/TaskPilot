from __future__ import annotations

import asyncio
import logging

from celery import Celery

from core.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "taskpilot",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=240,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def run_pipeline_task(self):
    """Celery task to run the full pipeline asynchronously."""
    try:
        from core.agent import run_pipeline

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        plan = loop.run_until_complete(run_pipeline())
        loop.close()
        logger.info("Pipeline task completed successfully")
        return {"status": "ok", "plan_generated": plan.generated_at if plan else None}
    except Exception as exc:
        logger.error("Pipeline task failed: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def sync_connector_task(self, source_type: str = None):
    """Celery task to trigger connector sync."""
    try:
        from core.sync_engine import sync_engine

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(sync_engine.sync_now(source_type))
        loop.close()
        logger.info("Sync task completed for %s", source_type or "all")
        return {"status": "ok", "source_type": source_type}
    except Exception as exc:
        logger.error("Sync task failed: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def generate_weekly_summary_task(self):
    """Celery task to generate weekly summary."""
    try:
        from core.weekly_summary import generate_weekly_summary
        from core.state import get_daily_snapshots

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        daily_plans = loop.run_until_complete(asyncio.to_thread(get_daily_snapshots, 7))
        summary = loop.run_until_complete(generate_weekly_summary(daily_plans))
        loop.close()
        logger.info("Weekly summary generated")
        return {"status": "ok", "summary": summary}
    except Exception as exc:
        logger.error("Weekly summary task failed: %s", exc)
        raise self.retry(exc=exc)
