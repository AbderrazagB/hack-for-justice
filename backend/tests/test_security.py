"""Security guardrails.

Each test here corresponds to something that was actually open or unbounded
before: officer endpoints served anyone, uploads were unvalidated and
unbounded, credentials could be tried without limit, and the acting officer on
a review was whatever the caller typed.
"""

from __future__ import annotations

import uuid
from io import BytesIO
from unittest.mock import patch

import pytest
from PIL import Image

from app.api.auth import current_user
from app.core.rate_limit import Limit, RateLimiter, limiter
from app.core.uploads import (
    MAX_FILE_BYTES,
    MAX_FILES_PER_SUBMISSION,
    sniff_type,
    validate_upload,
)
from app.main import app
from app.models.user import User, UserRole
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
def test_officer_surfaces_reject_anonymous_callers(
    anon_client, method: str, path: str
) -> None:
    """The queue, the stats and the stored documents expose every applicant's
    filing. None of them may serve an unauthenticated caller."""
    response = getattr(anon_client, method)(path)
    assert response.status_code == 401


def test_review_rejects_anonymous_callers(anon_client, store) -> None:
    """This endpoint decides whether a citizen's filing is accepted.

    The dossier is created through the store rather than the API, because the
    API now refuses an anonymous caller too -- and this test is about the
    review endpoint, not about how the filing got there.
    """
    submission = store.create(
        transaction_type="RNE_MODIFICATION_ENTREPRISE",
        documents={},
        completeness={"status": "COMPLETE"},
        flags=[],
        status="SUBMITTED",
    )

    response = anon_client.post(
        f"/submissions/{submission.id}/review", json={"action": "approve"}
    )
    assert response.status_code == 401


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


# ------------------------------------------------------ everything needs a session

@pytest.mark.parametrize(
    "path",
    [
        "/submissions/anything",
        "/submissions/anything/declaration.pdf",
    ],
)
def test_reading_a_filing_requires_a_session(anon_client, path: str) -> None:
    """A dossier carries identity documents and a home address."""
    assert anon_client.get(path).status_code == 401


def test_filing_requires_a_session(anon_client, png) -> None:
    """Filing used to be open to anyone, which left dossiers with no owner."""
    with patch.object(OCRService, "extract", _fake_extract):
        response = anon_client.post(
            ENDPOINT,
            files=[("files", ("a.png", png, "image/png"))],
            data={"document_types": ["rne_extract"]},
        )
    assert response.status_code == 401


def test_a_filing_belongs_to_whoever_made_it(client, png) -> None:
    with patch.object(OCRService, "extract", _fake_extract):
        created = client.post(
            ENDPOINT,
            files=[("files", ("a.png", png, "image/png"))],
            data={"document_types": ["rne_extract"]},
        )
    detail = client.get(f"/submissions/{created.json()['submission_id']}").json()
    assert detail["owner_id"] == str(client.stub_user.id)


def test_one_applicant_cannot_read_another_applicants_filing(
    client, store, tmp_path, png
) -> None:
    """The capability-URL branch is gone: an id is no longer an access grant."""
    with patch.object(OCRService, "extract", _fake_extract):
        created = client.post(
            ENDPOINT,
            files=[("files", ("a.png", png, "image/png"))],
            data={"document_types": ["rne_extract"]},
        )
    submission_id = created.json()["submission_id"]

    stranger = User(
        id=uuid.uuid4(),
        email="stranger@example.tn",
        password_hash="x",
        full_name="Stranger",
        role=UserRole.APPLICANT.value,
    )
    app.dependency_overrides[current_user] = lambda: stranger

    assert client.get(f"/submissions/{submission_id}").status_code == 403
    assert client.get(f"/submissions/{submission_id}/declaration.pdf").status_code == 403


def test_an_ownerless_filing_is_officer_only_not_public(client, store) -> None:
    """Seeded dossiers predate accounts. An absent owner is not a public dossier."""
    orphan = store.create(
        transaction_type="RNE_MODIFICATION_ENTREPRISE",
        documents={},
        completeness={"status": "COMPLETE"},
        flags=[],
        status="SUBMITTED",
        owner_id=None,
    ).id

    assert client.get(f"/submissions/{orphan}").status_code == 403

    officer = User(
        id=uuid.uuid4(),
        email="agent@rne.tn",
        password_hash="x",
        full_name="Agent",
        role=UserRole.OFFICER.value,
    )
    app.dependency_overrides[current_user] = lambda: officer
    assert client.get(f"/submissions/{orphan}").status_code == 200
