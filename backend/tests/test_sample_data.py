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

from data.generate_sample_data import (  # noqa: E402
    DOCUMENT_TYPES,
    REFERENCE_DATE,
    build_cases,
    generate_sample_data,
    write_dataset,
)

from app.services.rules_engine import check_completeness  # noqa: E402
from app.services.scoring import flag_inconsistencies  # noqa: E402


def _as_submission(case) -> dict:
    return {
        "transaction_type": "RNE_MODIFICATION_ENTREPRISE",
        "submitted_at": case.submitted_at,
        "documents": {
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
        },
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
    cases = write_dataset(tmp_path, count=5)
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
