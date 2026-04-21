"""Map rendered prompt DTOs to LangChain primitives (adapter boundary).

Also applies **conversation trimming** so upstream graph nodes stay thin: they pass raw
``state["messages"]`` through :func:`trim_conversation_messages` before ``ainvoke``.
Tool-output size limits are enforced separately (see ``tool_output_cap``).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from langchain_core.messages import BaseMessage, SystemMessage, trim_messages
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.modules.agent_orchestration.application.dtos.prompt_dto import RenderedPromptDTO


def trim_conversation_messages(
    messages: Sequence[BaseMessage],
    *,
    max_tokens: int,
    strategy: Literal["first", "last"] = "last",
) -> list[BaseMessage]:
    """Bound prompt size before LLM calls. Uses approximate token counting (fast, provider-agnostic).

    ``max_tokens <= 0`` skips trimming (escape hatch). Pairing rules for tool calls are
    delegated to LangChain's ``trim_messages`` with ``allow_partial=False``.
    """
    if max_tokens <= 0:
        return list(messages)
    return trim_messages(
        messages,
        max_tokens=max_tokens,
        token_counter="approximate",
        strategy=strategy,
        allow_partial=False,
    )


def trim_messages_for_supervisor_routing(
    messages: Sequence[BaseMessage],
    *,
    max_tokens: int,
) -> list[BaseMessage]:
    """Cheap routing window — same machinery as :func:`trim_conversation_messages` with a smaller budget."""
    return trim_conversation_messages(messages, max_tokens=max_tokens, strategy="last")


def to_system_message(dto: RenderedPromptDTO) -> SystemMessage:
    """Single system role message from rendered content."""
    return SystemMessage(content=dto.content)


def to_chat_prompt_template(dto: RenderedPromptDTO) -> ChatPromptTemplate:
    """Fixed system prompt + conversational ``messages`` placeholder."""
    return ChatPromptTemplate.from_messages(
        [
            ("system", dto.content),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )
