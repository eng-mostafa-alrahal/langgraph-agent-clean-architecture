"""Gunicorn configuration for production deployments."""

from __future__ import annotations

from app.core.config.settings import get_settings

_settings = get_settings()

bind = f"{_settings.HOST}:{_settings.PORT}"
workers = _settings.WORKERS
worker_class = "uvicorn.workers.UvicornWorker"
keepalive = 120
graceful_timeout = 30
timeout = 120
accesslog = "-"
errorlog = "-"
loglevel = _settings.LOG_LEVEL.lower()
