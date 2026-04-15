"""Rate-limiting middleware using SlowAPI."""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config.settings import get_settings

_settings = get_settings()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{_settings.RATE_LIMIT_PER_MINUTE}/minute"],
    storage_uri=_settings.get_redis_url(),
)
