"""Observability bootstrap — LangSmith tracing + OpenTelemetry."""

from __future__ import annotations

import os

from app.core.config.settings import get_settings


def setup_observability() -> None:
    settings = get_settings()

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
