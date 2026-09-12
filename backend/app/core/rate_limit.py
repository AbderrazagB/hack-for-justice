"""In-process rate limiting.

A fixed-window counter keyed by client and bucket. Deliberately simple and
deliberately in-memory: it resets on restart and does not coordinate across
workers, so it is a speed bump for credential stuffing and upload abuse, not a
defence against a distributed attacker. Put a real limiter at the edge before
this is exposed publicly -- this is the floor, not the ceiling.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from fastapi import HTTPException, Request, status


@dataclass(frozen=True)
class Limit:
    """`times` requests allowed per `seconds`."""

    times: int
    seconds: int


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[tuple[str, str], list[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str, bucket: str, limit: Limit) -> int | None:
        """Record a hit. Returns seconds to wait when over the limit, else None."""
        now = time.monotonic()
        window_start = now - limit.seconds
        index = (key, bucket)

        with self._lock:
            hits = [t for t in self._hits.get(index, []) if t > window_start]

            if len(hits) >= limit.times:
                self._hits[index] = hits
                return max(1, int(hits[0] + limit.seconds - now))

            hits.append(now)
            self._hits[index] = hits

            # Opportunistic cleanup so a long-lived process does not accumulate
            # a key per address seen since boot.
            if len(self._hits) > 4096:
                self._hits = {
                    k: v
                    for k, v in self._hits.items()
                    if v and v[-1] > now - 3600
                }

        return None

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = RateLimiter()


def client_key(request: Request) -> str:
    """Identify the caller.

    X-Forwarded-For is only trusted when the app is explicitly told it sits
    behind a proxy -- otherwise any client could spoof the header and evade the
    limit entirely by rotating it.
    """
    from app.core.config import settings

    if settings.trust_proxy_headers:
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()

    return request.client.host if request.client else "unknown"


def enforce(request: Request, bucket: str, limit: Limit) -> None:
    """Raise 429 when the caller has exceeded `limit` for `bucket`."""
    retry_after = limiter.check(client_key(request), bucket, limit)
    if retry_after is None:
        return

    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Trop de tentatives. Réessayez dans quelques instants.",
        headers={"Retry-After": str(retry_after)},
    )


# Tight on credentials, looser on reads. Signup is limited harder than login
# because an abusive signup creates durable state.
LOGIN_LIMIT = Limit(times=10, seconds=300)
SIGNUP_LIMIT = Limit(times=5, seconds=3600)
SUBMISSION_LIMIT = Limit(times=20, seconds=3600)
ASSISTANT_LIMIT = Limit(times=30, seconds=600)
