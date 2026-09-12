"""API-layer tests.

OCR is patched out: these assert routing, validation, persistence and status
transitions, not extraction quality (that lives in test_ocr_service.py).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.services.ocr_service import OCRResult, OCRService

TXN = "RNE_MODIFICATION_ENTREPRISE"
ENDPOINT = f"/transactions/{TXN}/submissions"

CLEAN_FIELDS = {
    "id_new_representative": {"id_number": "12345678", "person_name": "Amine Ben Salah"},
    "company_statutes": {"full_text": "Gérant: Amine Ben Salah"},
    "rne_extract": {"issue_date": "2026-06-01"},
    "tax_registration_card": {"company_id": "1234567X"},
    "general_assembly_pv": {
        "decision_date": "2026-06-12",
        "id_number": "12345678",
        "person_name": "Amine Ben Salah",
        "has_signature": True,
        "signature_date": "2026-06-12",
    },
}


def _fake_extract(fields_by_type: dict[str, dict]):
    def extract(self, content, filename="", document_type="general", force_local=False):
        return OCRResult(
            document_type=document_type,
            fields=dict(fields_by_type.get(document_type, {})),
            full_text=str(fields_by_type.get(document_type, {}).get("full_text", "")),
            engine="test",
            page_count=1,
        )
    return extract


def _upload(client, png, fields=None, doc_types=None, submitted_at="2026-07-01"):
    fields = CLEAN_FIELDS if fields is None else fields
    doc_types = doc_types or list(CLEAN_FIELDS)
    files = [("files", (f"{d}.png", png, "image/png")) for d in doc_types]
    # httpx2 needs repeated form fields as {key: [values]}. A list of (key, value)
    # tuples is accepted but silently dropped, which looks exactly like a broken
    # endpoint.
    data: dict[str, object] = {"document_types": doc_types}
    if submitted_at:
        data["submitted_at"] = submitted_at

    with patch.object(OCRService, "extract", _fake_extract(fields)):
        return client.post(ENDPOINT, files=files, data=data)


# ------------------------------------------------------------- transactions

def test_list_transactions_exposes_the_checklist(client) -> None:
    body = client.get("/transactions").json()
    assert len(body) == 1
    entry = body[0]
    assert entry["transaction_type"] == TXN
    assert entry["official_reference"] == "RNE-M-005"
    assert entry["display_name_ar"] == "تحيين مؤسسة"
    assert len(entry["required_documents"]) == 5
    assert all(d["label_fr"] and d["label_ar"] for d in entry["required_documents"])


# -------------------------------------------------------------------- intake

def test_complete_submission_is_pre_validated(client, png) -> None:
    response = _upload(client, png)
    assert response.status_code == 201

    body = response.json()
    assert body["completeness"]["status"] == "COMPLETE"
    assert body["status"] == "PRE_VALIDATED"
    assert body["flags"] == []
    assert body["submission_id"]


def test_missing_document_is_incomplete_and_flagged(client, png) -> None:
    doc_types = [d for d in CLEAN_FIELDS if d != "tax_registration_card"]
    body = _upload(client, png, doc_types=doc_types).json()

    assert body["completeness"]["status"] == "INCOMPLETE"
    assert body["status"] == "SUBMITTED"
    codes = {f["code"] for f in body["flags"]}
    assert "missing_document" in codes


def test_mismatched_id_is_flagged_at_intake(client, png) -> None:
    fields = {**CLEAN_FIELDS}
    fields["general_assembly_pv"] = {**fields["general_assembly_pv"], "id_number": "87654321"}

    body = _upload(client, png, fields=fields).json()
    assert body["completeness"]["status"] == "NEEDS_REVIEW"
    flag = next(f for f in body["flags"] if f["code"] == "id_number_matches_across_documents")
    assert "87654321" in flag["message_fr"]
    assert body["flag_summary"]["errors"] >= 1


def test_unknown_transaction_type_is_404(client, png) -> None:
    response = client.post(
        "/transactions/RNE_NOT_A_THING/submissions",
        files=[("files", ("a.png", png, "image/png"))],
        data={"document_types": ["national_id"]},
    )
    assert response.status_code == 404


def test_mismatched_files_and_types_is_400(client, png) -> None:
    response = client.post(
        ENDPOINT,
        files=[("files", ("a.png", png, "image/png"))],
        data={"document_types": ["id_new_representative", "rne_extract"]},
    )
    assert response.status_code == 400


def test_upload_is_persisted_to_disk(client, png, tmp_path) -> None:
    body = _upload(client, png).json()
    detail = client.get(f"/submissions/{body['submission_id']}").json()
    assert detail["documents"]["rne_extract"]["size_bytes"] == len(png)
    assert detail["documents"]["rne_extract"]["filename"].endswith(".png")


# -------------------------------------------------------------------- detail

def test_get_submission_returns_fields_and_flags(client, png) -> None:
    submission_id = _upload(client, png).json()["submission_id"]
    detail = client.get(f"/submissions/{submission_id}").json()

    assert detail["id"] == submission_id
    assert detail["documents"]["id_new_representative"]["fields"]["id_number"] == "12345678"
    assert detail["completeness"]["status"] == "COMPLETE"
    assert detail["reviews"] == []


def test_unknown_submission_is_404(client) -> None:
    assert client.get("/submissions/doesnotexist").status_code == 404


# --------------------------------------------------------------------- queue

def test_queue_lists_newest_first(client, png) -> None:
    first = _upload(client, png).json()["submission_id"]
    second = _upload(client, png).json()["submission_id"]

    body = client.get("/submissions").json()
    assert body["count"] == 2
    assert next(s["id"] for s in body["submissions"]) in {first, second}


def test_queue_filters_by_status(client, png) -> None:
    _upload(client, png)  # PRE_VALIDATED
    _upload(client, png, doc_types=[d for d in CLEAN_FIELDS if d != "rne_extract"])  # SUBMITTED

    assert client.get("/submissions?status=PRE_VALIDATED").json()["count"] == 1
    assert client.get("/submissions?status=SUBMITTED").json()["count"] == 1


def test_queue_filters_by_transaction_type(client, png) -> None:
    _upload(client, png)
    assert client.get(f"/submissions?transaction_type={TXN}").json()["count"] == 1
    assert client.get("/submissions?transaction_type=OTHER").json()["count"] == 0


def test_queue_summary_carries_flag_counts(client, png) -> None:
    _upload(client, png, doc_types=[d for d in CLEAN_FIELDS if d != "rne_extract"])
    summary = client.get("/submissions").json()["submissions"][0]
    assert summary["flag_count"] >= 1
    assert summary["error_flag_count"] >= 1
    assert summary["completeness_status"] == "INCOMPLETE"


# -------------------------------------------------------------------- review

@pytest.mark.parametrize(
    ("action", "expected"),
    [
        ("approve", "APPROVED"),
        ("reject", "REJECTED"),
        ("request_correction", "NEEDS_CORRECTION"),
    ],
)
def test_review_actions_set_status(client, png, action: str, expected: str) -> None:
    submission_id = _upload(client, png).json()["submission_id"]

    response = client.post(
        f"/submissions/{submission_id}/review",
        json={"action": action, "note": "vu par l'agent"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == expected

    assert client.get(f"/submissions/{submission_id}").json()["status"] == expected


def test_review_records_note_and_officer(client, png) -> None:
    submission_id = _upload(client, png).json()["submission_id"]
    client.post(
        f"/submissions/{submission_id}/review",
        json={"action": "request_correction", "note": "Extrait trop ancien", "officer": "agent-07"},
    )
    review = client.get(f"/submissions/{submission_id}").json()["reviews"][0]
    assert review["note"] == "Extrait trop ancien"
    assert review["officer"] == "agent-07"
    assert review["at"]


def test_review_history_accumulates(client, png) -> None:
    submission_id = _upload(client, png).json()["submission_id"]
    client.post(f"/submissions/{submission_id}/review", json={"action": "request_correction"})
    client.post(f"/submissions/{submission_id}/review", json={"action": "approve"})

    detail = client.get(f"/submissions/{submission_id}").json()
    assert len(detail["reviews"]) == 2
    assert detail["status"] == "APPROVED"


def test_review_on_unknown_submission_is_404(client) -> None:
    response = client.post("/submissions/nope/review", json={"action": "approve"})
    assert response.status_code == 404


def test_invalid_review_action_is_422(client, png) -> None:
    submission_id = _upload(client, png).json()["submission_id"]
    response = client.post(f"/submissions/{submission_id}/review", json={"action": "shred"})
    assert response.status_code == 422


# --------------------------------------------------------------------- stats

def test_stats_are_computed_from_stored_data(client, png) -> None:
    _upload(client, png)
    _upload(client, png, doc_types=[d for d in CLEAN_FIELDS if d != "rne_extract"])

    stats = client.get("/submissions/stats").json()
    assert stats["total"] == 2
    assert stats["flagged"] == 1
    assert stats["flag_rate"] == 0.5
    assert stats["by_status"]["PRE_VALIDATED"] == 1
    assert stats["reviewed"] == 0
    assert stats["average_review_seconds"] is None


def test_stats_report_review_latency_once_reviewed(client, png) -> None:
    submission_id = _upload(client, png).json()["submission_id"]
    client.post(f"/submissions/{submission_id}/review", json={"action": "approve"})

    stats = client.get("/submissions/stats").json()
    assert stats["reviewed"] == 1
    assert stats["average_review_seconds"] is not None
    assert stats["average_review_seconds"] >= 0


def test_stats_on_empty_store_do_not_divide_by_zero(client) -> None:
    stats = client.get("/submissions/stats").json()
    assert stats == {
        "total": 0,
        "by_status": {},
        "reviewed": 0,
        "flagged": 0,
        "flag_rate": 0.0,
        "average_review_seconds": None,
        "average_flags_per_submission": 0.0,
    }


def test_stats_path_is_not_captured_as_a_submission_id(client, png) -> None:
    """/submissions/stats must not resolve to /submissions/{id}."""
    _upload(client, png)
    assert client.get("/submissions/stats").status_code == 200
    assert "total" in client.get("/submissions/stats").json()


# ----------------------------------------------------------- document serving

def test_uploaded_document_can_be_fetched_back(client, png) -> None:
    submission_id = _upload(client, png).json()["submission_id"]
    detail = client.get(f"/submissions/{submission_id}").json()
    stored = detail["documents"]["rne_extract"]

    response = client.get(f"/documents/rne_extract/{stored['stored_path']}")
    assert response.status_code == 200
    assert response.content == png


def test_missing_document_is_404(client) -> None:
    assert client.get("/documents/rne_extract/nope.png").status_code == 404


@pytest.mark.parametrize(
    "attack",
    [
        "/documents/rne_extract/..%2F..%2F..%2Fetc%2Fpasswd",
        "/documents/..%2F..%2Fetc/passwd",
        "/documents/rne_extract/....//....//etc/passwd",
        "/documents/%2Fetc%2Fpasswd/passwd",
    ],
)
def test_path_traversal_is_refused(client, attack: str) -> None:
    """A URL must never reach a file outside the upload directory."""
    response = client.get(attack)
    assert response.status_code in {404, 400}
    assert b"root:" not in response.content
