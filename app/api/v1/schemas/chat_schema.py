"""HTTP request/response schemas for the chat / agent endpoint."""

from __future__ import annotations

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


class ChatResponse(BaseModel):
    session_id: UUID = Field(..., description="Session ID for this response.")
    reply: str = Field(..., description="Final assistant response text.")
