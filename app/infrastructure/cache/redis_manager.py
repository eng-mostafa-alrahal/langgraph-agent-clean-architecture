"""Redis connection manager for caching, rate-limiting, and pub/sub streaming."""

from __future__ import annotations

import redis.asyncio as aioredis

from app.core.config.settings import get_settings

_settings = get_settings()

redis_pool = aioredis.ConnectionPool.from_url(
    _settings.get_redis_url(),
    decode_responses=True,
    max_connections=20,
)


def get_redis() -> aioredis.Redis:  # type: ignore[type-arg]
    return aioredis.Redis(connection_pool=redis_pool)


async def close_redis() -> None:
    await redis_pool.aclose()
