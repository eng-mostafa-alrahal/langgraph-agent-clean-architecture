"""HTTP response schemas for authentication tokens."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    access_token: str = Field(
        ...,
        description="Short-lived JWT used to authorize protected endpoints.",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.example.access"],
    )
    refresh_token: str = Field(
        ...,
        description="Longer-lived JWT used to request a new token pair.",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.example.refresh"],
    )
    token_type: str = Field(default="bearer", description="Authorization scheme.")


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(
        ...,
        description="Refresh token previously issued by login or refresh endpoint.",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.example.refresh"],
    )
