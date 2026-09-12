"""Shared fixtures.

Every API test gets a throwaway store, so tests never touch the real
data/processed/submissions.json used by the demo.
"""

from __future__ import annotations

import uuid
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.api.auth import current_officer, current_user, optional_user
from app.api.submissions import get_upload_dir
from app.core.rate_limit import limiter
from app.main import app
from app.models.submission import SubmissionStore, get_store
from app.models.user import User, UserRole


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """The limiter is process-global; without this the suite trips its own
    limits and later tests fail with 429 for reasons unrelated to what they
    assert."""
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def store(tmp_path: Path) -> SubmissionStore:
    return SubmissionStore(tmp_path / "submissions.json")


@pytest.fixture
def client(store: SubmissionStore, tmp_path: Path) -> TestClient:
    """Store and uploads both redirected to tmp; tests never touch data/raw."""
    uploads = tmp_path / "uploads"
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_upload_dir] = lambda: uploads
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def png() -> bytes:
    """A small rendered document image, so uploads exercise the real OCR path."""
    image = Image.new("RGB", (700, 300), "white")
    draw = ImageDraw.Draw(image)
    draw.text((30, 40), "SARL EXEMPLE TUNISIE", fill="black")
    draw.text((30, 100), "CIN: 12345678", fill="black")
    draw.text((30, 160), "Date de la decision: 12/06/2026", fill="black")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _stub_user(role: UserRole) -> User:
    """A User instance that never touches the database.

    The officer-only routes are guarded by a dependency; these tests exercise
    the routes. That the dependency itself enforces the role, rejects a
    tampered token and rejects an applicant is covered in test_auth_api.py,
    against real Postgres.
    """
    user = User(
        id=uuid.uuid4(),
        email=f"{role.value}@rne.tn",
        password_hash="x",
        full_name=f"Test {role.value}",
        role=role.value,
    )
    return user


@pytest.fixture
def officer_client(store: SubmissionStore, tmp_path: Path) -> TestClient:
    """A client signed in as an RNE officer."""
    uploads = tmp_path / "uploads"
    officer = _stub_user(UserRole.OFFICER)

    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_upload_dir] = lambda: uploads
    app.dependency_overrides[current_officer] = lambda: officer
    app.dependency_overrides[current_user] = lambda: officer
    app.dependency_overrides[optional_user] = lambda: officer

    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
