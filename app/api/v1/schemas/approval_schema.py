"""HTTP request/response schemas for the human-approval endpoint."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ResumeRequest(BaseModel):
    action: Literal["approved", "rejected"] = Field(
        ...,
        description="Human decision: approve or reject the pending action.",
        examples=["approved"],
    )
    feedback: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional free-text feedback from the reviewer.",
        examples=["Looks good, proceed."],
    )


class ResumeResponse(BaseModel):
    thread_id: str = Field(..., description="Thread (session) ID of the resumed run.")
    reply: str = Field(..., description="Final assistant response after resuming.")
    interrupted: bool = Field(
        default=False,
        description="True when the resumed graph hit another interrupt.",
    )
    approval_request: dict[str, Any] | None = Field(
        default=None,
        description="Populated when *interrupted* is true — context for the next approval.",
    )


class RunStateResponse(BaseModel):
    thread_id: str
    interrupted: bool = False
    next_nodes: list[str] = Field(default_factory=list)
    tasks: list[dict[str, Any]] = Field(default_factory=list)
