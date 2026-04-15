"""HTTP request/response schemas for session endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    title: str = Field(
        default="New Chat",
        max_length=255,
        description="Optional session title shown in session lists.",
        examples=["Onboarding Q&A"],
    )


class SessionRenameRequest(BaseModel):
    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="New session title.",
        examples=["Pricing discussion"],
    )


class SessionResponse(BaseModel):
    id: UUID = Field(
        ...,
        description="Unique session identifier (UUIDv7).",
        examples=["019d92bc-2c73-74e6-814a-b647e46f0bf5"],
    )
    user_id: UUID = Field(
        ...,
        description="Owner user identifier (UUIDv7).",
        examples=["019d92aa-a6f4-74d3-a353-83f65edbb83e"],
    )
    title: str = Field(..., description="Session title.")
    created_at: datetime = Field(..., description="Creation timestamp in UTC.")
    updated_at: datetime = Field(..., description="Last update timestamp in UTC.")

    model_config = {"from_attributes": True}
