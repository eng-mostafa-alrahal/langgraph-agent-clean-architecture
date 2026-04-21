"""State-compaction node: summarize older turns and remove them from message history."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
)

from app.modules.agent_orchestration.domain.memory_policy import summary_cut_index

logger = logging.getLogger(__name__)


def _message_text(m: BaseMessage) -> str:
    content = m.content
    text = content.strip() if isinstance(content, str) else str(content).strip()
    role = getattr(m, "type", m.__class__.__name__).lower()
    return f"{role}: {text}" if text else f"{role}: (empty)"


def _build_summary_payload(messages: Sequence[BaseMessage], *, max_chars: int) -> str:
    joined = "\n".join(_message_text(m) for m in messages).strip()
    if max_chars > 0 and len(joined) > max_chars:
        return joined[:max_chars]
    return joined


def make_memory_manager_node(
    llm: BaseChatModel,
    *,
    keep_recent_messages: int,
    summary_max_chars: int,
):
    async def memory_manager_node(state: dict) -> dict:
        messages = state.get("messages", [])
        if not isinstance(messages, list):
            return {}
        cut = summary_cut_index(len(messages), keep_recent_messages=keep_recent_messages)
        if cut <= 0:
            return {}

        prefix = messages[:cut]
        removable_ids: list[str] = []
        for m in prefix:
            mid = getattr(m, "id", None)
            if isinstance(mid, str) and mid:
                removable_ids.append(mid)
        if not removable_ids:
            logger.info("memory_manager: no removable message IDs; skipping compaction")
            return {}

        payload = _build_summary_payload(prefix, max_chars=summary_max_chars)
        if not payload:
            return {"messages": [RemoveMessage(id=mid) for mid in removable_ids]}

        summary_prompt = (
            "Summarize the conversation history below into durable memory.\n"
            "Keep concrete facts, user preferences, open tasks, and decisions.\n"
            "Exclude filler, repetitions, and tool-call syntax.\n"
            "Use concise bullets."
        )
        summary = await llm.ainvoke(
            [
                SystemMessage(content=summary_prompt),
                HumanMessage(content=payload),
            ]
        )
        summary_text = getattr(summary, "content", "")
        summary_msg = AIMessage(content=f"Conversation summary:\n{summary_text}")
        removals = [RemoveMessage(id=mid) for mid in removable_ids]
        return {"messages": [*removals, summary_msg]}

    return memory_manager_node
