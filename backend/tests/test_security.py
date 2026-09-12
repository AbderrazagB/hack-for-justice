"""Security guardrails.

Each test here corresponds to something that was actually open or unbounded
before: officer endpoints served anyone, uploads were unvalidated and
unbounded, credentials could be tried without limit, and the acting officer on
a review was whatever the caller typed.
"""

from __future__ import annotations

from io import BytesIO
from unittest.mock import patch

import pytest
from PIL import Image

from app.core.rate_limit import Limit, RateLimiter, limiter
from app.core.uploads import (
    MAX_FILE_BYTES,
    MAX_FILES_PER_SUBMISSION,
    sniff_type,
    validate_upload,
)
from app.services.ocr_service import OCRResult, OCRService

TXN = "RNE_MODIFICATION_ENTREPRISE"
ENDPOINT = f"/transactions/{TXN}/submissions"


def _fake_extract(self, content, filename="", document_type="general", force_local=False):
    return OCRResult(document_type=document_type, fields={}, engine="test")


# ------------------------------------------------- officer-only endpoints ---

@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/submissions"),
        ("get", "/submissions/stats"),
        ("get", "/documents/rne_extract/anything.png"),
    ],
)
def test_officer_surfaces_reject_anonymous_callers(client, method: str, path: str) -> None:
    """The queue, the stats and the stored documents expose every applicant's
    filing. None of them may serve an unauthenticated caller."""
    response = getattr(client, method)(path)
    assert response.status_code == 401


def test_review_rejects_anonymous_callers(client, png) -> None:
    """This endpoint decides whether a citizen's filing is accepted."""
    with patch.object(OCRService, "extract", _fake_extract):
        created = client.post(
            ENDPOINT,
            files=[("files", ("a.png", png, "image/png"))],
            data={"document_types": ["rne_extract"]},
        )
    submission_id = created.json()["submission_id"]

    response = client.post(
        f"/submissions/{submission_id}/review", json={"action": "approve"}
    )
    assert response.status_code == 401


def test_submitting_stays_open_to_guests(client, png) -> None:
    """Checking a dossier without an account is a product requirement."""
    with patch.object(OCRService, "extract", _fake_extract):
        response = client.post(
            ENDPOINT,
            files=[("files", ("a.png", png, "image/png"))],
            data={"document_types": ["rne_extract"]},
        )
    assert response.status_code == 201


def test_reviewer_identity_comes_from_the_session(officer_client, png) -> None:
    """Otherwise the audit trail is whatever the caller typed."""
    with patch.object(OCRService, "extract", _fake_extract):
        created = officer_client.post(
            ENDPOINT,
            files=[("files", ("a.png", png, "image/png"))],
            data={"document_types": ["rne_extract"]},
        )
    submission_id = created.json()["submission_id"]

    officer_client.post(
        f"/submissions/{submission_id}/review",
        json={"action": "approve", "officer": "quelqu-un-dautre@exemple.tn"},
    )
    review = officer_client.get(f"/submissions/{submission_id}").json()["reviews"][0]
    assert review["officer"] == "officer@rne.tn"


# ------------------------------------------------------------ upload guards --

def test_declared_content_type_is_not_trusted(client) -> None:
    """A shell script named .png must not be accepted because the client says
    it is an image."""
    with patch.object(OCRService, "extract", _fake_extract):
        response = client.post(
            ENDPOINT,
            files=[("files", ("evil.png", b"#!/bin/sh\nrm -rf /", "image/png"))],
            data={"document_types": ["rne_extract"]},
        )
    assert response.status_code == 400
    assert "format" in response.json()["detail"].lower()


def test_empty_file_is_rejected(client) -> None:
    response = client.post(
        ENDPOINT,
        files=[("files", ("empty.png", b"", "image/png"))],
        data={"document_types": ["rne_extract"]},
    )
    assert response.status_code == 400


def test_oversized_file_is_rejected(client) -> None:
    oversized = b"\x89PNG\r\n\x1a\n" + b"\x00" * (MAX_FILE_BYTES + 1)
    response = client.post(
        ENDPOINT,
        files=[("files", ("big.png", oversized, "image/png"))],
        data={"document_types": ["rne_extract"]},
    )
    assert response.status_code == 413


def test_unknown_document_type_is_rejected(client, png) -> None:
    """An arbitrary type would be stored under an arbitrary directory name and
    then silently ignored by the rules engine."""
    response = client.post(
        ENDPOINT,
        files=[("files", ("a.png", png, "image/png"))],
        data={"document_types": ["../../etc/passwd"]},
    )
    assert response.status_code == 400


def test_too_many_files_is_rejected(client, png) -> None:
    count = MAX_FILES_PER_SUBMISSION + 2
    response = client.post(
        ENDPOINT,
        files=[("files", (f"{i}.png", png, "image/png")) for i in range(count)],
        data={"document_types": ["rne_extract"] * count},
    )
    assert response.status_code == 400


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (b"\x89PNG\r\n\x1a\n", "image/png"),
        (b"\xff\xd8\xff\xe0", "image/jpeg"),
        (b"%PDF-1.7", "application/pdf"),
        (b"GIF89a", "image/gif"),
        (b"RIFF\x00\x00\x00\x00WEBP", "image/webp"),
        (b"<html>", None),
        (b"MZ\x90\x00", None),  # a Windows executable
    ],
)
def test_type_is_detected_from_bytes(payload: bytes, expected: str | None) -> None:
    assert sniff_type(payload) == expected


def test_real_png_passes_validation() -> None:
    buffer = BytesIO()
    Image.new("RGB", (10, 10), "white").save(buffer, format="PNG")
    assert validate_upload(buffer.getvalue(), "page.png") == "image/png"


# ----------------------------------------------------------- rate limiting --

def test_limiter_allows_up_to_the_limit_then_blocks() -> None:
    local = RateLimiter()
    limit = Limit(times=3, seconds=60)

    assert all(local.check("1.2.3.4", "b", limit) is None for _ in range(3))
    retry_after = local.check("1.2.3.4", "b", limit)
    assert retry_after is not None and retry_after > 0


def test_limiter_is_per_client_and_per_bucket() -> None:
    local = RateLimiter()
    limit = Limit(times=1, seconds=60)

    assert local.check("1.1.1.1", "login", limit) is None
    assert local.check("1.1.1.1", "login", limit) is not None
    # A different caller, and a different bucket, are unaffected.
    assert local.check("2.2.2.2", "login", limit) is None
    assert local.check("1.1.1.1", "signup", limit) is None


def test_submissions_are_rate_limited(client, png) -> None:
    from app.core.rate_limit import SUBMISSION_LIMIT

    limiter.reset()
    with patch.object(OCRService, "extract", _fake_extract):
        for _ in range(SUBMISSION_LIMIT.times):
            ok = client.post(
                ENDPOINT,
                files=[("files", ("a.png", png, "image/png"))],
                data={"document_types": ["rne_extract"]},
            )
            assert ok.status_code == 201

        blocked = client.post(
            ENDPOINT,
            files=[("files", ("a.png", png, "image/png"))],
            data={"document_types": ["rne_extract"]},
        )
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


# -------------------------------------------------------- response headers --

def test_security_headers_are_present(client) -> None:
    response = client.get("/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_hsts_is_not_asserted_over_plain_http(client) -> None:
    """Pinning HSTS from an http deployment would lock browsers to a scheme
    this instance cannot serve."""
    assert "Strict-Transport-Security" not in client.get("/health").headers
