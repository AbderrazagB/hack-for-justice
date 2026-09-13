"""Locating a flag's disputed values on the page.

The point of the feature is verification, so the tests that matter are the
ones about *not* pointing at the wrong thing: a value that cannot be read
produces no box, and a short needle does not match every longer number on the
page.
"""

from __future__ import annotations

from io import BytesIO
from unittest.mock import patch

import pytest
from PIL import Image

from app.services.evidence import (
    locate,
    needles_from_flag,
    page_count,
    render_page,
)
from app.services.ocr_service import OCRResult, OCRService

TXN = "RNE_MODIFICATION_ENTREPRISE"
ENDPOINT = f"/transactions/{TXN}/submissions"


def _words(pairs, size=(1000, 500)):
    """Fake a Tesseract reading: (text, left, top, width, height)."""
    def fake(image_bytes, *args, **kwargs):
        return (
            [
                {"text": t, "left": x, "top": y, "width": w, "height": h}
                for t, x, y, w, h in pairs
            ],
            size[0],
            size[1],
        )
    return fake


# ------------------------------------------------------------------- needles

def test_needles_are_the_values_in_dispute() -> None:
    flag = {
        "evidence": {
            "reference_id": "98797309",
            "conflicts": [{"document": "general_assembly_pv", "id_number": "70753645"}],
        }
    }
    found = needles_from_flag(flag, {"general_assembly_pv", "id_new_representative"})
    assert found == ["98797309", "70753645"]


def test_document_keys_are_not_searched_for() -> None:
    """A key names where to look, not what to look for."""
    flag = {"evidence": {"document": "rne_extract"}}
    assert needles_from_flag(flag, {"rne_extract"}) == []


def test_trivially_short_values_are_skipped() -> None:
    """A two-character needle matches half the page."""
    flag = {"evidence": {"count": "7", "id": "ab"}}
    assert needles_from_flag(flag, set()) == []


def test_a_flag_with_no_evidence_asks_for_nothing() -> None:
    assert needles_from_flag({}, set()) == []


# -------------------------------------------------------------------- boxes

def test_a_value_on_the_page_is_boxed_as_page_fractions() -> None:
    reading = _words([("CIN:", 100, 50, 80, 20), ("98797309", 200, 50, 160, 20)])
    with patch("app.services.evidence._words", reading):
        boxes = locate(b"png", ["98797309"])

    assert len(boxes) == 1
    box = boxes[0]
    assert box.x == pytest.approx(0.2)
    assert box.y == pytest.approx(0.1)
    assert box.width == pytest.approx(0.16)
    assert box.height == pytest.approx(0.04)
    assert box.text == "98797309"


def test_a_value_that_is_not_there_produces_no_box() -> None:
    """The honest failure. A rectangle over the wrong place defeats the point."""
    reading = _words([("CIN:", 100, 50, 80, 20), ("11111111", 200, 50, 160, 20)])
    with patch("app.services.evidence._words", reading):
        assert locate(b"png", ["98797309"]) == []


def test_a_short_needle_does_not_match_a_longer_number() -> None:
    """Otherwise "123" would box every identifier on the page."""
    reading = _words([("9879730912345", 200, 50, 300, 20)])
    with patch("app.services.evidence._words", reading):
        assert locate(b"png", ["98797309"]) == []


def test_punctuation_around_a_value_does_not_prevent_a_match() -> None:
    """OCR reads "n°98797309," as one word as often as not."""
    reading = _words([("n°98797309,", 200, 50, 200, 20)])
    with patch("app.services.evidence._words", reading):
        assert len(locate(b"png", ["98797309"])) == 1


def test_a_multi_word_value_spans_the_words_it_covers() -> None:
    reading = _words([("Amine", 100, 40, 100, 20), ("Ben", 210, 40, 60, 20), ("Salah", 280, 40, 90, 20)])
    with patch("app.services.evidence._words", reading):
        boxes = locate(b"png", ["Amine Ben Salah"])

    assert len(boxes) == 1
    assert boxes[0].x == pytest.approx(0.1)
    assert boxes[0].width == pytest.approx((370 - 100) / 1000)


def test_no_ocr_engine_returns_no_boxes_rather_than_failing() -> None:
    """Tesseract is optional. Its absence must not 500 the endpoint."""
    def explode(*args, **kwargs):
        raise RuntimeError("tesseract is not installed")

    with patch("app.services.evidence._words", explode):
        assert locate(b"png", ["98797309"]) == []


def test_locate_with_no_needles_does_no_work() -> None:
    def explode(*args, **kwargs):
        raise AssertionError("should not have read the page")

    with patch("app.services.evidence._words", explode):
        assert locate(b"png", []) == []


# --------------------------------------------------------------------- pages

def test_an_image_is_its_own_page_zero() -> None:
    buffer = BytesIO()
    Image.new("RGB", (50, 20), "white").save(buffer, format="PNG")
    content = buffer.getvalue()

    image, media_type = render_page(content, 0)
    assert image == content
    assert media_type == "image/png"
    assert page_count(content) == 1


def test_an_image_has_no_second_page() -> None:
    buffer = BytesIO()
    Image.new("RGB", (50, 20), "white").save(buffer, format="PNG")
    with pytest.raises(ValueError):
        render_page(buffer.getvalue(), 1)


# ------------------------------------------------------------------ endpoint

def _fake_extract(self, content, filename="", document_type="general", force_local=False):
    fields = {
        "id_new_representative": {"id_number": "12345678", "person_name": "Amine Ben Salah"},
        "general_assembly_pv": {"id_number": "87654321", "person_name": "Amine Ben Salah"},
    }.get(document_type, {})
    return OCRResult(document_type=document_type, fields=dict(fields), engine="test")


def _create(client, png):
    doc_types = ["id_new_representative", "general_assembly_pv"]
    files = [("files", (f"{d}.png", png, "image/png")) for d in doc_types]
    with patch.object(OCRService, "extract", _fake_extract):
        return client.post(
            ENDPOINT, files=files, data={"document_types": doc_types}
        ).json()["submission_id"]


def test_evidence_names_the_values_and_the_pages(client, png) -> None:
    submission_id = _create(client, png)
    body = client.get(
        f"/submissions/{submission_id}/evidence/id_number_matches_across_documents"
    ).json()

    assert set(body["values"]) == {"12345678", "87654321"}
    keys = {document["key"] for document in body["documents"]}
    assert keys == {"id_new_representative", "general_assembly_pv"}
    for document in body["documents"]:
        assert document["pages"][0]["image_url"].endswith(
            f"/pages/{document['key']}/0.png"
        )


def test_evidence_for_an_unraised_flag_is_404(client, png) -> None:
    submission_id = _create(client, png)
    assert (
        client.get(f"/submissions/{submission_id}/evidence/not_a_check").status_code
        == 404
    )


def test_evidence_requires_a_session(anon_client) -> None:
    assert anon_client.get("/submissions/x/evidence/y").status_code == 401


def test_a_page_is_served_back_to_its_owner(client, png) -> None:
    """Unlike /documents/..., which is officer-only: this is your own dossier."""
    submission_id = _create(client, png)
    response = client.get(
        f"/submissions/{submission_id}/pages/id_new_representative/0.png"
    )
    assert response.status_code == 200
    assert response.content == png


def test_a_page_requires_a_session(anon_client) -> None:
    assert anon_client.get("/submissions/x/pages/y/0.png").status_code == 401


def test_an_unknown_document_has_no_page(client, png) -> None:
    submission_id = _create(client, png)
    assert (
        client.get(f"/submissions/{submission_id}/pages/not_a_document/0.png").status_code
        == 404
    )
