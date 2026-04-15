"""Celery worker initialisation."""

from __future__ import annotations

from celery import Celery

from app.core.config.settings import get_settings

settings = get_settings()

celery_app = Celery(
    "agent_workers",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery_app.autodiscover_tasks(["workers"])
