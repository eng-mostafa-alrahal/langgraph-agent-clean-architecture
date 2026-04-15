"""Format provider errors for API responses (e.g. Groq tool_use_failed + failed_generation)."""

from __future__ import annotations

def format_agent_execution_detail(exc: BaseException) -> str:
    """Return a human-readable detail string, appending nested provider payloads when present."""
    base = str(exc).strip()
    extra: list[str] = []

    for link in _walk_exception_chain(exc):
        body = getattr(link, "body", None)
        if isinstance(body, dict):
            err = body.get("error")
            if isinstance(err, dict):
                fg = err.get("failed_generation")
                if fg is not None and str(fg).strip():
                    extra.append(f"failed_generation: {fg!r}")

    if extra:
        return f"{base} ({'; '.join(extra)})" if base else "; ".join(extra)
    return base if base else repr(exc)


def _walk_exception_chain(exc: BaseException | None) -> list[BaseException]:
    out: list[BaseException] = []
    seen: set[int] = set()
    cur: BaseException | None = exc
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        out.append(cur)
        cur = cur.__cause__ or cur.__context__
    return out
