from __future__ import annotations

from uuid import UUID

from pydantic import Field

from app.shared.domain_models.base_model import DomainModel


class Session(DomainModel):
    user_id: UUID
    title: str = Field(default="New Chat", max_length=255)
