"""Immutable base entity that every domain model inherits from."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.shared.uuid_utils import uuid7


class DomainModel(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID = Field(default_factory=uuid7)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
