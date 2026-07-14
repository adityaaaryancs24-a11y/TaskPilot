from celery.schedules import crontab

from backend.celery_app import celery_app

celery_app.conf.beat_schedule = {
    "run-pipeline-every-15-minutes": {
        "task": "celery_app.run_pipeline_task",
        "schedule": crontab(minute="*/15"),
    },
    "sync-connectors-every-30-minutes": {
        "task": "celery_app.sync_connector_task",
        "schedule": crontab(minute="*/30"),
    },
    "generate-weekly-summary-monday": {
        "task": "celery_app.generate_weekly_summary_task",
        "schedule": crontab(hour=8, minute=0, day_of_week=1),
    },
}
