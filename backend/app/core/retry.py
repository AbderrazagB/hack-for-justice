"""Retry helper for rate-limited provider calls.

Sahilli fans out several vision calls per submission (one per document), which
is exactly the shape that trips a provider's per-minute limit. A 429 mid-demo
would otherwise surface as "extraction dégradée" on a document that is
perfectly readable, so we back off and retry rather than give up on the first
refusal.

Only retries what is worth retrying: rate limits and transient server errors.
A 401 or a malformed request is retried zero times -- repeating it just wastes
the clock.
"""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

RETRYABLE_MARKERS = (
    "429",
    "rate limit",
    "rate_limited",
    "too many requests",
    "500",
    "502",
    "503",
    "504",
    "timeout",
    "timed out",
)


def is_retryable(error: Exception) -> bool:
    """True for rate limits and transient server errors, false for the rest."""
    text = str(error).lower()
    # An invalid key will never succeed on retry, however it is phrased.
    if "api key not valid" in text or "invalid api key" in text or "401" in text:
        return False
    return any(marker in text for marker in RETRYABLE_MARKERS)


def with_retry(
    call: Callable[[], T],
    attempts: int = 4,
    base_delay: float = 2.0,
    description: str = "provider call",
) -> T:
    """Run `call`, retrying retryable failures with exponential backoff.

    Jitter is added so several documents submitted together do not retry in
    lockstep and trip the same limit again.
    """
    last: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            return call()
        except Exception as exc:
            last = exc
            if attempt == attempts or not is_retryable(exc):
                raise
            delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
            logger.warning(
                "%s failed (attempt %d/%d), retrying in %.1fs: %s",
                description,
                attempt,
                attempts,
                delay,
                exc,
            )
            time.sleep(delay)

    raise last if last else RuntimeError(f"{description} failed")
