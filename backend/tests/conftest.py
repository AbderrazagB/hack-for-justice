"""Shared fixtures.

Every API test gets a throwaway store, so tests never touch the real
data/processed/submissions.json used by the demo.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.main import app
from app.models.submission import SubmissionStore, get_store


@pytest.fixture
def store(tmp_path: Path) -> SubmissionStore:
    return SubmissionStore(tmp_path / "submissions.json")


@pytest.fixture
def client(store: SubmissionStore) -> TestClient:
    app.dependency_overrides[get_store] = lambda: store
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
