"""Flagging tests: the officer dashboard's view of what is wrong."""

from __future__ import annotations

from datetime import date

from app.services.rules_engine import TRANSACTION_RULES, check_completeness
from app.services.scoring import (
    Severity,
    flag_inconsistencies,
    flag_summary,
    flags_from_result,
)

TODAY = date(2026, 7, 1)

CLEAN = {
    "id_new_representative": {
        "fields": {"id_number": "12345678", "person_name": "Amine Ben Salah"}
    },
    "company_statutes": {"fields": {"full_text": "Gérant: Amine Ben Salah"}},
    "rne_extract": {"fields": {"issue_date": "2026-06-01"}},
    "tax_registration_card": {"fields": {"company_id": "1234567X"}},
    "general_assembly_pv": {
        "fields": {
            "decision_date": "2026-06-12",
            "id_number": "12345678",
            "person_name": "Amine Ben Salah",
        }
    },
}


def _with(**overrides) -> dict:
    documents = {key: dict(value) for key, value in CLEAN.items()}
    documents.update(overrides)
    return documents


def _codes(flags) -> set[str]:
    return {flag.code for flag in flags}


# ------------------------------------------------------------- clean filing

def test_clean_submission_raises_no_flags() -> None:
    assert flag_inconsistencies(CLEAN, today=TODAY) == []


def test_summary_of_clean_submission_is_all_zero() -> None:
    assert flag_summary(flag_inconsistencies(CLEAN, today=TODAY)) == {
        "total": 0, "errors": 0, "warnings": 0, "info": 0
    }


# ---------------------------------------------------------- the ID mismatch

def test_id_mismatch_message_names_both_numbers() -> None:
    documents = _with(
        general_assembly_pv={
            "fields": {"decision_date": "2026-06-12", "id_number": "87654321"}
        }
    )
    flag = next(
        f
        for f in flag_inconsistencies(documents, today=TODAY)
        if f.code == "id_number_matches_across_documents"
    )

    assert flag.severity is Severity.ERROR
    assert "12345678" in flag.message_fr
    assert "87654321" in flag.message_fr
    assert flag.message_ar  # bilingual for the FR/AR interface


def test_id_mismatch_points_at_both_documents_to_compare() -> None:
    documents = _with(
        general_assembly_pv={
            "fields": {"decision_date": "2026-06-12", "id_number": "87654321"}
        }
    )
    flag = next(
        f
        for f in flag_inconsistencies(documents, today=TODAY)
        if f.code == "id_number_matches_across_documents"
    )
    assert flag.documents == ["id_new_representative", "general_assembly_pv"]


# ------------------------------------------------------------ other checks

def test_stale_extract_is_flagged_with_its_age() -> None:
    documents = _with(rne_extract={"fields": {"issue_date": "2025-01-01"}})
    flag = next(
        f
        for f in flag_inconsistencies(documents, today=TODAY)
        if f.code == "rne_extract_not_older_than_90_days"
    )
    assert flag.severity is Severity.ERROR
    assert flag.evidence["age_days"] == 546


def test_late_filing_is_flagged_with_penalty_months() -> None:
    documents = _with(
        general_assembly_pv={
            "fields": {"decision_date": "2026-01-05", "id_number": "12345678"}
        }
    )
    flag = next(
        f
        for f in flag_inconsistencies(documents, today=TODAY)
        if f.code == "filed_within_30_days_of_decision_date"
    )
    assert flag.evidence["penalty_months"] == 5
    assert "52-2018" in flag.message_fr


def test_statutes_naming_the_wrong_person_is_flagged() -> None:
    documents = _with(company_statutes={"fields": {"full_text": "Gérant: Slim Trabelsi"}})
    flags = flag_inconsistencies(documents, today=TODAY)
    assert "statutes_reflect_new_representative_name" in _codes(flags)


# ------------------------------------------------------ missing + severity

def test_missing_document_produces_a_labelled_error_flag() -> None:
    documents = _with()
    del documents["tax_registration_card"]

    flag = next(
        f for f in flag_inconsistencies(documents, today=TODAY) if f.code == "missing_document"
    )
    assert flag.severity is Severity.ERROR
    assert flag.documents == ["tax_registration_card"]
    assert flag.to_dict()["documents"][0]["label_ar"]


def test_unreadable_field_is_a_warning_not_an_error() -> None:
    """We must not accuse a citizen of a mismatch we could not actually read."""
    documents = _with(
        id_new_representative={"fields": {"id_number": None, "person_name": "Amine Ben Salah"}}
    )
    flag = next(
        f
        for f in flag_inconsistencies(documents, today=TODAY)
        if f.code == "id_number_matches_across_documents"
    )
    assert flag.severity is Severity.WARNING


def test_errors_are_ordered_before_warnings() -> None:
    documents = _with(
        rne_extract={"fields": {"issue_date": None}},                       # warning
        company_statutes={"fields": {"full_text": "Gérant: Slim Trabelsi"}},  # error
    )
    severities = [f.severity for f in flag_inconsistencies(documents, today=TODAY)]
    assert severities == sorted(
        severities, key=lambda s: {Severity.ERROR: 0, Severity.WARNING: 1, Severity.INFO: 2}[s]
    )


def test_fully_broken_submission_flags_every_declared_check() -> None:
    documents = _with(
        company_statutes={"fields": {"full_text": "Gérant: Slim Trabelsi"}},
        rne_extract={"fields": {"issue_date": "2025-01-01"}},
        general_assembly_pv={
            "fields": {"decision_date": "2026-01-05", "id_number": "87654321"}
        },
    )
    flags = flag_inconsistencies(documents, today=TODAY)
    assert _codes(flags) == set(TRANSACTION_RULES["RNE_MODIFICATION_ENTREPRISE"]["checks"])
    assert flag_summary(flags)["errors"] == 4


# ---------------------------------------------------------------- plumbing

def test_accepts_a_full_submission_dict_too() -> None:
    submission = {"transaction_type": "RNE_MODIFICATION_ENTREPRISE", "documents": CLEAN}
    assert flag_inconsistencies(submission, today=TODAY) == []


def test_submitted_at_is_honoured_when_passed_as_submission() -> None:
    submission = {
        "transaction_type": "RNE_MODIFICATION_ENTREPRISE",
        "documents": CLEAN,
        "submitted_at": "2026-06-20",
    }
    flags = flag_inconsistencies(submission, today=date(2026, 12, 31))
    assert "filed_within_30_days_of_decision_date" not in _codes(flags)


def test_flags_from_result_avoids_revalidating() -> None:
    """The API path reuses one completeness result rather than computing twice."""
    result = check_completeness(
        {"transaction_type": "RNE_MODIFICATION_ENTREPRISE", "documents": CLEAN},
        today=TODAY,
    )
    assert flags_from_result(result) == []


def test_flag_serialises_for_the_api() -> None:
    documents = _with(
        general_assembly_pv={
            "fields": {"decision_date": "2026-06-12", "id_number": "87654321"}
        }
    )
    payload = flag_inconsistencies(documents, today=TODAY)[0].to_dict()
    assert payload["severity"] == "ERROR"
    assert payload["message_fr"] and payload["message_ar"]
    assert payload["documents"][0]["key"]
