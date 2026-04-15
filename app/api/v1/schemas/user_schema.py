"""HTTP request/response schemas for user endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="Display name used in the UI.",
        examples=["John Doe"],
    )
    email: EmailStr = Field(
        ...,
        description="Unique email used for login.",
        examples=["john@example.com"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Plain password (minimum 8 characters).",
        examples=["StrongPass123!"],
    )


class UserLoginRequest(BaseModel):
    email: EmailStr = Field(
        ...,
        description="Email used during registration.",
        examples=["john@example.com"],
    )
    password: str = Field(
        ...,
        description="User password.",
        examples=["StrongPass123!"],
    )


class UserResponse(BaseModel):
    id: UUID = Field(
        ...,
        description="Unique user identifier (UUIDv7).",
        examples=["019d92aa-a6f4-74d3-a353-83f65edbb83e"],
    )
    name: str = Field(..., description="User display name.")
    email: EmailStr = Field(..., description="User email address.")
    is_active: bool = Field(..., description="Whether the account is active.")
    created_at: datetime = Field(..., description="Creation timestamp in UTC.")
    updated_at: datetime = Field(..., description="Last update timestamp in UTC.")

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=120,
        description="Updated display name.",
        examples=["Jane Doe"],
    )
    email: EmailStr | None = Field(
        default=None,
        description="Updated unique email address.",
        examples=["jane@example.com"],
    )
    is_active: bool | None = Field(
        default=None,
        description="Set user active status.",
        examples=[True],
    )
