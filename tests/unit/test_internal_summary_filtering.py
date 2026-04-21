from app.api.v1.routers.chat_router import _compact_event_payload
from app.modules.agent_orchestration.application.dtos.agent_result import (
    AgentEvent,
    AgentMessage,
    AgentRunResult,
)


def test_last_ai_reply_skips_internal_memory_summary() -> None:
    result = AgentRunResult(
        messages=[
            AgentMessage(type="human", content="Hi"),
            AgentMessage(type="ai", content="Hello!"),
            AgentMessage(
                type="ai",
                content=(
                    "Conversation summary:\n"
                    "- User greeted the AI.\n"
                    "- No other details."
                ),
            ),
        ]
    )

    assert result.last_ai_reply == "Hello!"


def test_compact_event_payload_skips_internal_memory_summary() -> None:
    event = AgentEvent(
        node="supervisor",
        messages=[
            AgentMessage(type="ai", content="Assistant reply"),
            AgentMessage(
                type="ai",
                content="Conversation summary:\n- Internal summary content",
            ),
        ],
    )

    payload = _compact_event_payload(event)

    assert payload is not None
    assert payload == {"content": "Assistant reply"}
