"""Observability bootstrap — LangSmith tracing + OpenTelemetry."""

from __future__ import annotations

import logging
import os
import sys

from app.core.config.settings import get_settings


def _quiet_noisy_loggers() -> None:
    """Reduce third-party log noise while preserving app latency traces."""
    noisy_levels = {
        # HTTP clients used by LLM/tool providers
        "httpcore": logging.WARNING,
        "httpx": logging.WARNING,
        "urllib3": logging.WARNING,
        # Optional tracing backend chatter
        "langsmith": logging.WARNING,
        # SQL statement spam (keep warnings/errors only)
        "sqlalchemy.engine": logging.WARNING,
    }
    for name, level in noisy_levels.items():
        logging.getLogger(name).setLevel(level)


def setup_observability() -> None:
    settings = get_settings()
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        )
    else:
        root_logger.setLevel(log_level)
    logging.getLogger("app").setLevel(log_level)
    # Uvicorn installs access logs on stdout by default. Many debug sessions surface stderr
    # more reliably — route access logs to stderr (single handler) for visibility.
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.setLevel(logging.INFO)
    access_logger.handlers.clear()
    from uvicorn.logging import AccessFormatter

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(AccessFormatter(use_colors=False))
    access_logger.addHandler(stderr_handler)
    access_logger.propagate = False
    _quiet_noisy_loggers()
    logging.getLogger(__name__).info(
        "Observability initialized level=%s", settings.LOG_LEVEL.upper()
    )

    # LangSmith
    if settings.LANGSMITH_API_KEY:
        os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
        os.environ.setdefault("LANGCHAIN_API_KEY", settings.LANGSMITH_API_KEY)
        os.environ.setdefault("LANGCHAIN_PROJECT", settings.LANGSMITH_PROJECT)

    # OpenTelemetry (basic setup; extend with custom exporters as needed)
    if settings.OTEL_EXPORTER_ENDPOINT:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

        resource = Resource.create({"service.name": settings.APP_NAME})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        trace.set_tracer_provider(provider)
