"""API coverage for the financial statements workflow.

The point of these is that the endpoints were built generically: the same
routes serve a second transaction type with no per-workflow branching.
"""

from __future__ import annotations

from unittest.mock import patch

from app.services.ocr_service import OCRResult, OCRService

TXN = "RNE_FINANCIAL_STATEMENTS"
ENDPOINT = f"/transactions/{TXN}/submissions"

CLEAN_FIELDS = {
    "financial_statements_signed": {"has_signature": True, "has_stamp": True},
    "general_assembly_pv_approval": {
        "full_text": "Assemblée générale ordinaire",
        "registration_reference": "RF-2026-0042",
    },
    "auditor_report": {"full_text": "Rapport du commissaire aux comptes"},
    "updated_shareholder_list": {
        "shareholders": [
            {"name": "Amine Ben Salah", "id_number": "12345678"},
            {"name": "Salma Trabelsi", "id_number": "87654321"},
        ]
    },
}


def _fake_extract(fields_by_type):
    def extract(self, content, filename="", document_type="general", force_local=False):
        return OCRResult(
            document_type=document_type,
            fields=dict(fields_by_type.get(document_type, {})),
            engine="test",
            page_count=1,
        )
    return extract


def _submit(client, png, fields=None, doc_types=None, **context):
    fields = CLEAN_FIELDS if fields is None else fields
    doc_types = doc_types or list(CLEAN_FIELDS)
    files = [("files", (f"{d}.png", png, "image/png")) for d in doc_types]
    data: dict[str, object] = {
        "document_types": doc_types,
        "submitted_at": context.pop("submitted_at", "2026-07-01"),
        "company_type": context.pop("company_type", "SA"),
        "fiscal_year_end": context.pop("fiscal_year_end", "2025-12-31"),
    }
    data.update({k: str(v).lower() for k, v in context.items()})

    with patch.object(OCRService, "extract", _fake_extract(fields)):
        return client.post(ENDPOINT, files=files, data=data)


# ------------------------------------------------------------- transactions

def test_transactions_endpoint_lists_both_workflows(client) -> None:
    body = client.get("/transactions").json()
    types = {t["transaction_type"] for t in body}
    assert {"RNE_MODIFICATION_ENTREPRISE", TXN} <= types


def test_transaction_exposes_its_context_fields(client) -> None:
    """The pre-step form is data, so the frontend needs no per-workflow code."""
    entry = next(
        t for t in client.get("/transactions").json() if t["transaction_type"] == TXN
    )
    names = {f["name"] for f in entry["context_fields"]}
    assert names == {"company_type", "fiscal_year_end", "auditor_required"}

    company = next(f for f in entry["context_fields"] if f["name"] == "company_type")
    assert company["type"] == "select"
    assert any(o["value"] == "SA" for o in company["options"])
    assert entry["conditional_documents"] == ["auditor_report"]


def test_modification_workflow_has_no_context_fields(client) -> None:
    entry = next(
        t
        for t in client.get("/transactions").json()
        if t["transaction_type"] == "RNE_MODIFICATION_ENTREPRISE"
    )
    assert entry["context_fields"] == []
    assert entry["conditional_documents"] == []


# -------------------------------------------------------------------- intake

def test_clean_filing_is_pre_validated(client, png) -> None:
    response = _submit(client, png)
    assert response.status_code == 201

    body = response.json()
    assert body["completeness"]["status"] == "COMPLETE"
    assert body["status"] == "PRE_VALIDATED"
    assert body["flags"] == []
    assert body["completeness"]["display_name_ar"] == "إيداع القوائم المالية السنوية"


def test_context_is_persisted_on_the_submission(client, png) -> None:
    submission_id = _submit(client, png).json()["submission_id"]
    detail = client.get(f"/submissions/{submission_id}").json()

    assert detail["context"]["company_type"] == "SA"
    assert detail["context"]["fiscal_year_end"] == "2025-12-31"


def test_missing_auditor_report_fails_for_an_sa(client, png) -> None:
    doc_types = [d for d in CLEAN_FIELDS if d != "auditor_report"]
    body = _submit(client, png, doc_types=doc_types, company_type="SA").json()

    assert body["completeness"]["status"] == "INCOMPLETE"
    assert "auditor_report" in [
        m["key"] for m in body["completeness"]["missing_documents"]
    ]


def test_absent_auditor_report_is_fine_for_a_sarl(client, png) -> None:
    """The conditional document must not be demanded when it is not owed."""
    doc_types = [d for d in CLEAN_FIELDS if d != "auditor_report"]
    body = _submit(client, png, doc_types=doc_types, company_type="SARL").json()

    assert body["completeness"]["status"] == "COMPLETE"
    assert body["completeness"]["missing_documents"] == []
    assert "auditor_report" not in body["required_documents"]


def test_sarl_over_thresholds_does_owe_the_auditor_report(client, png) -> None:
    doc_types = [d for d in CLEAN_FIELDS if d != "auditor_report"]
    body = _submit(
        client, png, doc_types=doc_types, company_type="SARL", auditor_required=True
    ).json()

    assert body["completeness"]["status"] == "INCOMPLETE"
    assert "auditor_report" in body["required_documents"]


def test_late_filing_is_flagged_with_its_penalty(client, png) -> None:
    body = _submit(
        client, png, fiscal_year_end="2025-12-31", submitted_at="2026-10-15"
    ).json()

    flag = next(
        f
        for f in body["flags"]
        if f["code"] == "filed_within_7_months_of_fiscal_year_close"
    )
    assert flag["evidence"]["penalty_total_tnd"] == 75
    assert "25 DT/mois" in flag["message_fr"]


def test_shareholder_without_id_is_flagged(client, png) -> None:
    fields = {**CLEAN_FIELDS}
    fields["updated_shareholder_list"] = {
        "shareholders": [
            {"name": "Amine Ben Salah", "id_number": "12345678"},
            {"name": "Salma Trabelsi", "id_number": None},
        ]
    }
    body = _submit(client, png, fields=fields).json()
    codes = {f["code"] for f in body["flags"]}
    assert "shareholder_list_ids_present_for_each_entry" in codes


def test_unregistered_pv_is_a_warning_not_an_error(client, png) -> None:
    fields = {**CLEAN_FIELDS}
    fields["general_assembly_pv_approval"] = {"full_text": "Procès-verbal"}
    body = _submit(client, png, fields=fields).json()

    flag = next(
        f
        for f in body["flags"]
        if f["code"] == "pv_registered_with_recette_des_finances_if_applicable"
    )
    assert flag["severity"] == "WARNING"


# -------------------------------------------------------------- queue/review

def test_queue_filters_by_transaction_type(client, png) -> None:
    _submit(client, png)
    assert client.get(f"/submissions?transaction_type={TXN}").json()["count"] == 1
    assert (
        client.get(
            "/submissions?transaction_type=RNE_MODIFICATION_ENTREPRISE"
        ).json()["count"]
        == 0
    )


def test_review_works_for_this_workflow(client, png) -> None:
    submission_id = _submit(client, png).json()["submission_id"]
    response = client.post(
        f"/submissions/{submission_id}/review",
        json={"action": "approve", "note": "Comptes conformes"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "APPROVED"


def test_stats_count_both_workflows_together(client, png) -> None:
    _submit(client, png)
    assert client.get("/submissions/stats").json()["total"] == 1
