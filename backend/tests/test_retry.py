"""Retry helper tests."""

from __future__ import annotations

import pytest

from app.core.retry import is_retryable, with_retry


@pytest.mark.parametrize(
    "message",
    [
        "API error occurred: Status 429. Rate limit exceeded",
        "rate_limited",
        "Too Many Requests",
        "Status 503 service unavailable",
        "connection timed out",
    ],
)
def test_transient_failures_are_retryable(message: str) -> None:
    assert is_retryable(RuntimeError(message)) is True


@pytest.mark.parametrize(
    "message",
    [
        "401 Unauthorized",
        "Invalid API Key",
        "API key not valid. Please pass a valid API key.",
        "400 malformed request",
    ],
)
def test_permanent_failures_are_not_retryable(message: str) -> None:
    assert is_retryable(RuntimeError(message)) is False


def test_succeeds_after_a_transient_failure() -> None:
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("Status 429 rate limit exceeded")
        return "ok"

    assert with_retry(flaky, base_delay=0.001) == "ok"
    assert calls["n"] == 3


def test_gives_up_after_the_attempt_budget() -> None:
    calls = {"n": 0}

    def always_limited():
        calls["n"] += 1
        raise RuntimeError("429 rate limit")

    with pytest.raises(RuntimeError):
        with_retry(always_limited, attempts=3, base_delay=0.001)
    assert calls["n"] == 3


def test_permanent_failure_is_not_retried() -> None:
    calls = {"n": 0}

    def bad_key():
        calls["n"] += 1
        raise RuntimeError("Invalid API Key")

    with pytest.raises(RuntimeError):
        with_retry(bad_key, attempts=4, base_delay=0.001)
    assert calls["n"] == 1  # tried once, not four times


def test_returns_immediately_when_the_call_succeeds() -> None:
    assert with_retry(lambda: 42) == 42
