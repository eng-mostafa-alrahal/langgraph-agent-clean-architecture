"""Pure-Python DTOs for the agent orchestrator boundary.

These types contain no LangGraph / LangChain dependencies. They form the
Anti-Corruption Layer: the infrastructure adapter maps framework objects
(BaseMessage, Command, snapshot tuples, ...) into these DTOs so that the
application and delivery layers never see framework types.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

MessageRole = Literal["human", "ai", "system", "tool"]


class AgentMessage(BaseModel):
    """Framework-agnostic representation of a single chat turn."""

    model_config = ConfigDict(frozen=True)

    type: MessageRole
    content: str
    id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    model: str | None = None
    usage: dict[str, int] | None = None


class ApprovalRequest(BaseModel):
    """Payload surfaced when the graph pauses on a human-review gate."""

    model_config = ConfigDict(frozen=True, extra="allow")

    reason: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class AgentRunResult(BaseModel):
    """Final output of a single graph invocation (sync or resumed)."""

    model_config = ConfigDict(frozen=True)

    messages: list[AgentMessage]
    interrupted: bool = False
    thread_id: str | None = None
    approval_request: ApprovalRequest | dict[str, Any] | None = None

    @property
    def last_ai_reply(self) -> str:
        for msg in reversed(self.messages):
            if msg.type == "ai":
                return msg.content
        return self.messages[-1].content if self.messages else ""


class AgentEvent(BaseModel):
    """One incremental update emitted while the graph is executing."""

    model_config = ConfigDict(frozen=True)

    node: str
    messages: list[AgentMessage] = Field(default_factory=list)
    updates: dict[str, Any] = Field(default_factory=dict)


class AgentTaskSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    interrupts: list[dict[str, Any]] = Field(default_factory=list)


class AgentStateSnapshot(BaseModel):
    """Current state of a thread as exposed by the orchestrator."""

    model_config = ConfigDict(frozen=True)

    thread_id: str
    interrupted: bool
    next_nodes: list[str] = Field(default_factory=list)
    tasks: list[AgentTaskSnapshot] = Field(default_factory=list)
