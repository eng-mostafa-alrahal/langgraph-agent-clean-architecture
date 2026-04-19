"""Map rendered prompt DTOs to LangChain primitives (adapter boundary)."""

from __future__ import annotations

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.modules.agent_orchestration.application.dtos.prompt_dto import RenderedPromptDTO


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
