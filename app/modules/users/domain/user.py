"""User domain entity — owned by the users module."""

from __future__ import annotations

from pydantic import EmailStr, Field

from app.shared.domain_models.base_model import DomainModel


class User(DomainModel):
    name: str = Field(..., min_length=1, max_length=120)
    email: EmailStr
    hashed_password: str = Field(..., exclude=True)
    is_active: bool = True
