"""UUID helpers shared across layers."""

from __future__ import annotations

import secrets
import time
from uuid import UUID


def uuid7() -> UUID:
    """Generate an RFC 9562 UUID version 7."""
    ts_ms = int(time.time_ns() // 1_000_000)
    rand_a = secrets.randbits(12)
    rand_b = secrets.randbits(62)

    value = 0
    value |= (ts_ms & ((1 << 48) - 1)) << 80
    value |= 0x7 << 76
    value |= rand_a << 64
    value |= 0b10 << 62
    value |= rand_b

    return UUID(int=value)
