"""Demo data tests.

The demo set is only useful if each case actually produces the verdict it
claims. These tests run the generated cases through the real rules engine, so a
rule change that silently invalidates the stage demo fails here first.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data.generate_sample_data import (
    DOCUMENT_TYPES,
    REFERENCE_DATE,
    build_cases,
    generate_sample_data,
    write_dataset,
)

from app.services.rules_engine import check_completeness
from app.services.scoring import flag_inconsistencies
from tests.conftest import with_page_text


def _as_submission(case) -> dict:
    return {
        "transaction_type": "RNE_MODIFICATION_ENTREPRISE",
        "submitted_at": case.submitted_at,
        "documents": with_page_text({
            "id_new_representative": {
                "fields": {"id_number": case.cin, "person_name": case.new_representative}
            },
            "company_statutes": {
                "fields": {"full_text": f"Gerant: {case.statutes_representative}"}
            },
            "rne_extract": {"fields": {"issue_date": case.extract_issue_date}},
            "tax_registration_card": {"fields": {"company_id": case.tax_id}},
            "general_assembly_pv": {
                "fields": {
                    "decision_date": case.decision_date,
                    "id_number": case.cin_in_pv,
                    "person_name": case.new_representative,
                    "signature_date": case.signature_date,
                    "has_signature": case.signature_date is not None,
                }
            },
        }),
    }


def test_generation_is_deterministic() -> None:
    """Same seed, same data -- so a rehearsed demo stays the rehearsed demo."""
    first = [c.to_dict() for c in build_cases(seed=2026)]
    second = [c.to_dict() for c in build_cases(seed=2026)]
    assert first == second


def test_dataset_has_both_broken_and_clean_cases() -> None:
    cases = build_cases()
    broken = [c for c in cases if c.intent != "clean"]
    clean = [c for c in cases if c.intent == "clean"]
    assert len(broken) >= 3
    assert len(clean) >= 1


@pytest.mark.parametrize("case", build_cases(), ids=lambda c: c.case_id)
def test_each_case_produces_the_verdict_it_claims(case) -> None:
    submission = _as_submission(case)
    result = check_completeness(submission, today=REFERENCE_DATE)
    assert result.status.value == case.expected_status, case.label


@pytest.mark.parametrize(
    "case", [c for c in build_cases() if c.expected_flags], ids=lambda c: c.case_id
)
def test_each_broken_case_raises_its_expected_flags(case) -> None:
    codes = {f.code for f in flag_inconsistencies(_as_submission(case), today=REFERENCE_DATE)}
    assert set(case.expected_flags) <= codes, f"{case.label}: got {codes}"


def test_clean_cases_raise_no_flags_at_all() -> None:
    for case in build_cases():
        if case.intent != "clean":
            continue
        flags = flag_inconsistencies(_as_submission(case), today=REFERENCE_DATE)
        assert flags == [], f"{case.case_id} should be clean, got {[f.code for f in flags]}"


def test_the_three_specified_defects_are_present() -> None:
    intents = {c.intent for c in build_cases()}
    assert "mismatched_id_numbers" in intents
    assert "missing_signature_date" in intents
    assert "filed_late" in intents


def test_identifiers_look_tunisian_but_are_synthetic() -> None:
    for case in build_cases():
        assert case.cin.isdigit() and len(case.cin) == 8      # CIN shape
        assert len(case.company_id) == 8                       # RNE identifier
        assert case.tax_id.startswith(case.company_id)


def test_write_dataset_renders_every_document(tmp_path: Path) -> None:
    # write_dataset now emits both workflows; this one pins the modification set.
    cases = [
        c
        for c in write_dataset(tmp_path, count=5, financial_count=0)
        if c.transaction_type == "RNE_MODIFICATION_ENTREPRISE"
    ]
    for case in cases:
        assert set(case.documents) == set(DOCUMENT_TYPES)
        for path in case.documents.values():
            rendered = Path(path)
            assert rendered.exists()
            assert rendered.read_bytes()[:4] == b"\x89PNG"
    assert (tmp_path / "manifest.json").exists()


def test_dataframe_helper_still_works() -> None:
    frame = generate_sample_data(count=5)
    assert len(frame) == 5
    assert {"case_id", "cin", "decision_date"} <= set(frame.columns)


# ------------------------------------ financial statements demo cases

from data.generate_sample_data import (
    FINANCIAL_DOCUMENT_TYPES,
    build_financial_cases,
)


def _as_financial_submission(case) -> dict:
    documents = {
        "financial_statements_signed": {
            "fields": {
                "has_signature": case.statements_signed,
                "has_stamp": case.statements_stamped,
                "fiscal_year_end": case.fiscal_year_end,
            }
        },
        "general_assembly_pv_approval": {
            "fields": {
                "registration_reference": case.pv_registration_reference,
                "full_text": "Assemblée générale ordinaire",
            }
        },
        "updated_shareholder_list": {"fields": {"shareholders": case.shareholders}},
    }
    if case.auditor_name:
        documents["auditor_report"] = {
            "fields": {"full_text": f"Rapport de {case.auditor_name}"}
        }

    return {
        "transaction_type": "RNE_FINANCIAL_STATEMENTS",
        "documents": with_page_text(documents),
        "submitted_at": case.submitted_at,
        "company_type": case.company_type,
        "auditor_required": case.auditor_required,
        "fiscal_year_end": case.fiscal_year_end,
    }


def test_financial_generation_is_deterministic() -> None:
    first = [c.to_dict() for c in build_financial_cases(seed=2026)]
    second = [c.to_dict() for c in build_financial_cases(seed=2026)]
    assert first == second


def test_financial_set_has_broken_and_clean_cases() -> None:
    cases = build_financial_cases()
    assert len([c for c in cases if c.intent != "clean"]) >= 2
    assert len([c for c in cases if c.intent == "clean"]) >= 1


def test_the_two_specified_financial_defects_are_present() -> None:
    intents = {c.intent for c in build_financial_cases()}
    assert "missing_auditor_report" in intents
    assert "filed_late" in intents


@pytest.mark.parametrize(
    "case", build_financial_cases(), ids=lambda c: c.case_id
)
def test_each_financial_case_produces_the_verdict_it_claims(case) -> None:
    result = check_completeness(_as_financial_submission(case), today=REFERENCE_DATE)
    assert result.status.value == case.expected_status, case.label


@pytest.mark.parametrize(
    "case",
    [c for c in build_financial_cases() if c.expected_flags],
    ids=lambda c: c.case_id,
)
def test_each_broken_financial_case_raises_its_flags(case) -> None:
    codes = {
        f.code
        for f in flag_inconsistencies(
            _as_financial_submission(case), today=REFERENCE_DATE
        )
    }
    assert set(case.expected_flags) <= codes, f"{case.label}: got {codes}"


def test_clean_financial_cases_raise_no_flags() -> None:
    for case in build_financial_cases():
        if case.intent != "clean":
            continue
        flags = flag_inconsistencies(
            _as_financial_submission(case), today=REFERENCE_DATE
        )
        assert flags == [], f"{case.case_id}: {[f.code for f in flags]}"


def test_write_dataset_renders_both_workflows(tmp_path: Path) -> None:
    cases = write_dataset(tmp_path, count=5, financial_count=5)

    modification = [c for c in cases if c.transaction_type == "RNE_MODIFICATION_ENTREPRISE"]
    financial = [c for c in cases if c.transaction_type == "RNE_FINANCIAL_STATEMENTS"]
    assert modification and financial

    for case in modification:
        assert set(case.documents) == set(DOCUMENT_TYPES)

    for case in financial:
        # The auditor report is only rendered when the case actually owes one.
        expected = set(FINANCIAL_DOCUMENT_TYPES)
        if not case.auditor_name:
            expected.discard("auditor_report")
        assert set(case.documents) == expected
        for path in case.documents.values():
            assert Path(path).read_bytes()[:4] == b"\x89PNG"
