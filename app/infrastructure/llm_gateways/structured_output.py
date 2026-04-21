"""Provider-aware structured output helper."""

from __future__ import annotations

from typing import Any, TypeVar

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def with_pydantic_output(llm: BaseChatModel, schema: type[T]) -> Any:
    """Return structured-output wrapper for the provided chat model."""
    return llm.with_structured_output(schema)
