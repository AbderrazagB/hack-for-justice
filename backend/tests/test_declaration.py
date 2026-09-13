"""The RNE-F-005 declaration: capture, cross-check and preparation sheet.

The value here is not the PDF. It is that Sahilli now compares what an
applicant *declares* against what their documents *say* -- the contradiction
the registry rejects on, which reading the attachments alone cannot catch.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

from pypdf import PdfReader

from app.services.declaration import (
    CROSS_CHECKED,
    DECLARATION_FIELDS,
    FIELD_GROUPS,
    cross_check,
    missing_required,
)
from app.services.declaration_pdf import build_preparation_sheet, shape_arabic
from app.services.ocr_service import OCRResult, OCRService
from app.services.rules_engine import CheckOutcome, Status, check_completeness

TXN = "RNE_MODIFICATION_ENTREPRISE"
TODAY = date(2026, 7, 1)

DOCUMENTS = {
    "id_new_representative": {
        "fields": {"id_number": "12345678", "person_name": "Amine Ben Salah"}
    },
    "company_statutes": {"fields": {"full_text": "Gérant: Amine Ben Salah"}},
    "rne_extract": {"fields": {"issue_date": "2026-06-01", "company_id": "1234567B"}},
    "tax_registration_card": {"fields": {"company_id": "1234567B"}},
    "general_assembly_pv": {
        "fields": {
            "decision_date": "2026-06-12",
            "id_number": "12345678",
            "person_name": "Amine Ben Salah",
            "has_signature": True,
            "signature_date": "2026-06-12",
        }
    },
}

DECLARATION = {
    "legal_representative": "Amine Ben Salah",
    "email": "amine@exemple.tn",
    "phone": "20123456",
    "declarant_name": "Amine Ben Salah",
    "declarant_id": "12345678",
    "unique_identifier": "1234567",
}


def _submission(declaration=DECLARATION, documents=None):
    payload = {
        "transaction_type": TXN,
        "documents": documents or DOCUMENTS,
        "submitted_at": "2026-07-01",
    }
    if declaration is not None:
        payload["declaration"] = declaration
    return payload


def _declaration_check(result):
    return next(c for c in result.checks if c.name == "declaration_matches_documents")


# --------------------------------------------------------------- field spec

def test_fields_match_the_printed_form() -> None:
    """RNE-F-005 prints exactly these nine entries."""
    assert [f.name for f in DECLARATION_FIELDS] == [
        "legal_representative",
        "email",
        "phone",
        "declarant_name",
        "declarant_id",
        "entity_id",
        "unique_identifier",
        "reservation_certificate",
        "rib",
    ]


def test_email_and_phone_are_mandatory() -> None:
    """The form says so in bold: they are how the RNE reaches you."""
    required = {f.name for f in DECLARATION_FIELDS if f.required}
    assert {"email", "phone"} <= required


def test_optional_fields_are_the_conditional_ones() -> None:
    optional = {f.name for f in DECLARATION_FIELDS if not f.required}
    assert optional == {"entity_id", "reservation_certificate", "rib"}


def test_every_field_is_bilingual() -> None:
    for spec in DECLARATION_FIELDS:
        assert spec.label_fr and spec.label_ar, spec.name


# ------------------------------------------------------------- completeness

def test_missing_required_field_is_reported() -> None:
    missing = missing_required({**DECLARATION, "email": ""})
    assert [f.name for f in missing] == ["email"]


def test_blank_optional_fields_are_not_reported() -> None:
    assert missing_required(DECLARATION) == []


def test_incomplete_declaration_fails_the_check() -> None:
    result = check_completeness(
        _submission({**DECLARATION, "phone": ""}), today=TODAY
    )
    check = _declaration_check(result)
    assert check.outcome is CheckOutcome.FAIL
    assert "rejet" in check.reason_fr
    assert check.evidence["missing_fields"] == ["phone"]


# -------------------------------------------------------------- cross-check

def test_clean_declaration_passes() -> None:
    result = check_completeness(_submission(), today=TODAY)
    assert _declaration_check(result).outcome is CheckOutcome.PASS
    assert result.status is Status.COMPLETE


def test_declared_id_differing_from_the_card_is_caught() -> None:
    result = check_completeness(
        _submission({**DECLARATION, "declarant_id": "87654321"}), today=TODAY
    )
    check = _declaration_check(result)
    assert check.outcome is CheckOutcome.FAIL
    assert "87654321" in check.reason_fr and "12345678" in check.reason_fr


def test_declared_identifier_differing_from_the_extract_is_caught() -> None:
    result = check_completeness(
        _submission({**DECLARATION, "unique_identifier": "9999999"}), today=TODAY
    )
    assert _declaration_check(result).outcome is CheckOutcome.FAIL


def test_declared_representative_absent_from_the_documents_is_caught() -> None:
    result = check_completeness(
        _submission({**DECLARATION, "legal_representative": "Slim Trabelsi"}),
        today=TODAY,
    )
    check = _declaration_check(result)
    assert check.outcome is CheckOutcome.FAIL
    assert "représentant légal" in check.reason_fr.lower()


def test_unreadable_documents_do_not_accuse_the_declarant() -> None:
    """An empty OCR result is not evidence that the declaration is wrong."""
    blank = {key: {"fields": {}} for key in DOCUMENTS}
    assert cross_check(DECLARATION, blank) == []


def test_id_comparison_ignores_formatting() -> None:
    assert cross_check({**DECLARATION, "declarant_id": "12 345 678"}, DOCUMENTS) == []


# ---------------------------------------- the check is optional, by design

def test_no_declaration_means_the_check_does_not_run() -> None:
    """Sahilli must let someone check documents before filling the form."""
    result = check_completeness(_submission(declaration=None), today=TODAY)
    assert result.status is Status.COMPLETE
    assert all(c.name != "declaration_matches_documents" for c in result.checks)


# ------------------------------------------------------- preparation sheet

def test_sheet_renders_with_the_declared_values() -> None:
    submission = {
        "completeness": {
            "display_name_fr": "Modification Entreprise",
            "official_reference": "RNE-M-005",
        },
        "context": {"declaration": DECLARATION},
        "documents": {"id_new_representative": {}},
    }
    text = PdfReader(io_of(build_preparation_sheet(submission))).pages[0].extract_text()

    assert "Amine Ben Salah" in text
    assert "12345678" in text
    assert "amine@exemple.tn" in text


def test_sheet_says_it_is_not_a_filing() -> None:
    """It must not be mistaken for the declaration itself: since July 2026 the
    real one is filed on the portal and signed digitally."""
    text = PdfReader(
        io_of(build_preparation_sheet({"context": {"declaration": DECLARATION}}))
    ).pages[0].extract_text()

    assert "n'est pas un dépôt officiel" in text
    assert "portail du RNE" in text


def test_sheet_marks_fields_still_to_complete() -> None:
    partial = {k: v for k, v in DECLARATION.items() if k != "phone"}
    text = PdfReader(
        io_of(build_preparation_sheet({"context": {"declaration": partial}}))
    ).pages[0].extract_text()
    assert "à compléter" in text


def test_arabic_is_shaped_for_pdf_rendering() -> None:
    """Unshaped Arabic renders as disconnected letters in reverse order."""
    assert shape_arabic("بيانات التصريح") != "بيانات التصريح"
    assert shape_arabic("Latin only") == "Latin only"


def io_of(data: bytes):
    import io

    return io.BytesIO(data)


# -------------------------------------------------------------------- API

def _fake_extract(self, content, filename="", document_type="general", force_local=False):
    return OCRResult(
        document_type=document_type,
        fields=dict(DOCUMENTS.get(document_type, {}).get("fields", {})),
        engine="test",
    )


def _post(client, png, declaration=None):
    import json

    doc_types = list(DOCUMENTS)
    files = [("files", (f"{d}.png", png, "image/png")) for d in doc_types]
    data: dict[str, object] = {
        "document_types": doc_types,
        "submitted_at": "2026-07-01",
    }
    if declaration is not None:
        data["declaration"] = json.dumps(declaration)

    with patch.object(OCRService, "extract", _fake_extract):
        return client.post(f"/transactions/{TXN}/submissions", files=files, data=data)


def test_transaction_exposes_the_declaration_form(client) -> None:
    entry = next(
        t for t in client.get("/transactions").json() if t["transaction_type"] == TXN
    )
    names = [f["name"] for f in entry["declaration_fields"]]
    assert names == [f.name for f in DECLARATION_FIELDS]
    assert entry["modification_type_fr"] == "Ajout ou mise à jour des dirigeants"
    assert entry["modification_type_ar"]


def test_declaration_is_stored_and_checked(client, png) -> None:
    body = _post(client, png, DECLARATION).json()
    assert body["completeness"]["status"] == "COMPLETE"

    detail = client.get(f"/submissions/{body['submission_id']}").json()
    assert detail["context"]["declaration"]["email"] == "amine@exemple.tn"


def test_mismatched_declaration_is_flagged_through_the_api(client, png) -> None:
    body = _post(client, png, {**DECLARATION, "declarant_id": "87654321"}).json()
    codes = {f["code"] for f in body["flags"]}
    assert "declaration_matches_documents" in codes


def test_unknown_declaration_keys_are_discarded(client, png) -> None:
    """Only the form's own fields are stored; this goes into a generated PDF."""
    body = _post(client, png, {**DECLARATION, "evil": "<script>"}).json()
    detail = client.get(f"/submissions/{body['submission_id']}").json()
    assert "evil" not in detail["context"]["declaration"]


def test_malformed_declaration_is_rejected(client, png) -> None:
    doc_types = list(DOCUMENTS)
    files = [("files", (f"{d}.png", png, "image/png")) for d in doc_types]
    with patch.object(OCRService, "extract", _fake_extract):
        response = client.post(
            f"/transactions/{TXN}/submissions",
            files=files,
            data={"document_types": doc_types, "declaration": "not json"},
        )
    assert response.status_code == 400


def test_preparation_sheet_downloads(client, png) -> None:
    submission_id = _post(client, png, DECLARATION).json()["submission_id"]
    response = client.get(f"/submissions/{submission_id}/declaration.pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert response.content[:5] == b"%PDF-"


def test_preparation_sheet_of_an_unknown_submission_is_404(client) -> None:
    assert client.get("/submissions/nope/declaration.pdf").status_code == 404


# ------------------------------------------------------------------- "pourquoi"

def test_every_field_explains_why_it_is_asked() -> None:
    """The disclosure next to each question is part of the contract, not decoration."""
    for spec in DECLARATION_FIELDS:
        assert spec.why_fr, f"{spec.name} has no French explanation"
        assert spec.why_ar, f"{spec.name} has no Arabic explanation"


def test_cross_checked_fields_say_so_and_the_others_do_not_pretend() -> None:
    """A field we never compare must not read as though we verified it.

    Saying otherwise would turn a clean result into false assurance, which is
    the one failure mode this step exists to prevent.
    """
    for spec in DECLARATION_FIELDS:
        mentions_comparison = "compar" in (spec.why_fr or "").lower()
        assert mentions_comparison == spec.cross_checked, spec.name
        assert bool(spec.compared_with_fr) == spec.cross_checked, spec.name


def test_cross_checked_set_matches_what_cross_check_actually_compares() -> None:
    """The badge is derived from CROSS_CHECKED, so CROSS_CHECKED must be true.

    Feed a declaration that disagrees with the documents on every field and
    assert the issues raised name exactly the fields advertised as compared.
    """
    documents = {
        "id_new_representative": {
            "fields": {"id_number": "11111111", "person_name": "Salah Ben Amine"}
        },
        "rne_extract": {"fields": {"company_id": "7777777"}},
        "general_assembly_pv": {"fields": {"person_name": "Salah Ben Amine"}},
    }
    declaration = {spec.name: "Zzz Contradiction" for spec in DECLARATION_FIELDS}
    declaration["declarant_id"] = "22222222"
    declaration["unique_identifier"] = "8888888"

    raised = {issue.field_name for issue in cross_check(declaration, documents)}
    assert raised == set(CROSS_CHECKED)


def test_every_field_belongs_to_a_known_group() -> None:
    for spec in DECLARATION_FIELDS:
        assert spec.group in FIELD_GROUPS, spec.name


def test_groups_are_contiguous_in_form_order() -> None:
    """Sections must not reorder the form.

    RNE-F-005 prints the nine entries in an order that already groups cleanly;
    the UI draws headings over that order rather than rearranging it, so a
    group appearing twice would mean the list has drifted from the form.
    """
    seen: list[str] = []
    for spec in DECLARATION_FIELDS:
        if not seen or seen[-1] != spec.group:
            seen.append(spec.group)
    assert len(seen) == len(set(seen)), seen
