"""Provider-aware structured output — Groq rejects pseudo-XML function_calling for schemas."""

from __future__ import annotations

from typing import Any, TypeVar

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def with_pydantic_output(llm: BaseChatModel, schema: type[T]) -> Any:
    """Use JSON mode on Groq (avoids tool_use_failed / ``<function=Schema>`` garbage)."""
    try:
        from langchain_groq import ChatGroq

        if isinstance(llm, ChatGroq):
            return llm.with_structured_output(schema, method="json_mode")
    except ImportError:
        pass
    return llm.with_structured_output(schema)
