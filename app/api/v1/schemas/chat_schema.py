"""HTTP request/response schemas for the chat / agent endpoint."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=10_000,
        description="User prompt sent to the agent.",
        examples=["Summarize this document in 5 bullets."],
    )
    session_id: UUID = Field(
        ...,
        description="Target conversation session ID (UUIDv7).",
        examples=["019d92bc-2c73-74e6-814a-b647e46f0bf5"],
    )
    stream_detail: Literal["content", "full"] = Field(
        default="content",
        description=(
            "For POST /chat/stream only: `content` (default) emits a small JSON per chunk "
            "(`node`, `assistant` with the latest AI reply and optional usage/tool_calls). "
            "`full` sends the raw per-node state (full message list, session_id, reasoning, etc.)."
        ),
    )


class ChatResponse(BaseModel):
    session_id: UUID = Field(..., description="Session ID for this response.")
    reply: str = Field(..., description="Final assistant response text.")
    interrupted: bool = Field(
        default=False,
        description="True when the graph paused and requires human approval to continue.",
    )
    thread_id: str | None = Field(
        default=None,
        description="Thread ID to use when calling the /resume endpoint (same as session_id).",
    )
    approval_request: dict[str, Any] | None = Field(
        default=None,
        description="Context for the pending approval decision (populated when interrupted=true).",
    )
