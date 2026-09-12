"""Rules engine tests.

This module decides whether a citizen's filing is complete, so the tests pin
each rule's exact behaviour including its boundaries.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.services.rules_engine import (
    FILING_DEADLINE_MONTHS,
    RNE_EXTRACT_MAX_AGE_DAYS,
    TRANSACTION_RULES,
    CheckOutcome,
    Status,
    UnknownTransactionType,
    check_completeness,
)

TODAY = date(2026, 7, 1)
TXN = "RNE_MODIFICATION_ENTREPRISE"


def _submission(**overrides) -> dict:
    """A fully valid submission; override pieces to break one thing at a time."""
    documents = {
        "id_new_representative": {
            "fields": {"id_number": "12345678", "person_name": "Amine Ben Salah"}
        },
        "company_statutes": {
            "fields": {
                "full_text": "Gérant: Amine Ben Salah, SARL Exemple Tunisie",
                "id_number": None,
            }
        },
        "rne_extract": {"fields": {"issue_date": "2026-06-01"}},
        "tax_registration_card": {"fields": {"company_id": "1234567X"}},
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
    documents.update(overrides.pop("documents", {}))
    submission = {
        "transaction_type": TXN,
        "documents": documents,
        "submitted_at": "2026-07-01",
    }
    submission.update(overrides)
    return submission


def _outcome(result, check_name) -> CheckOutcome:
    return next(c for c in result.checks if c.name == check_name).outcome


# ----------------------------------------------------------- rule definition

def test_transaction_rules_match_the_official_checklist() -> None:
    rules = TRANSACTION_RULES[TXN]
    assert rules["display_name_fr"] == "Modification Entreprise"
    assert rules["display_name_ar"] == "تحيين مؤسسة"
    assert rules["official_reference"] == "RNE-M-005"
    assert rules["required_documents"] == [
        "id_new_representative",
        "company_statutes",
        "rne_extract",
        "tax_registration_card",
        "general_assembly_pv",
    ]
    assert rules["checks"] == [
        "id_number_matches_across_documents",
        "statutes_reflect_new_representative_name",
        "rne_extract_not_older_than_90_days",
        "filed_within_30_days_of_decision_date",
        "pv_is_signed",
        "declaration_matches_documents",
    ]


def test_unknown_transaction_type_is_rejected() -> None:
    with pytest.raises(UnknownTransactionType):
        check_completeness({"transaction_type": "RNE_SOMETHING_ELSE"}, today=TODAY)


# --------------------------------------------------------------- happy path

def test_clean_submission_is_complete() -> None:
    result = check_completeness(_submission(), today=TODAY)
    assert result.status is Status.COMPLETE
    assert result.missing_documents == []
    assert len(result.present_documents) == 5
    assert all(c.outcome is CheckOutcome.PASS for c in result.checks)


# ------------------------------------------------------ missing documents

def test_missing_document_makes_it_incomplete() -> None:
    submission = _submission()
    del submission["documents"]["general_assembly_pv"]

    result = check_completeness(submission, today=TODAY)
    assert result.status is Status.INCOMPLETE
    assert result.missing_documents == ["general_assembly_pv"]


def test_all_documents_missing_lists_every_one() -> None:
    result = check_completeness(
        {"transaction_type": TXN, "documents": {}}, today=TODAY
    )
    assert result.status is Status.INCOMPLETE
    assert len(result.missing_documents) == 5


def test_document_explicitly_flagged_missing_counts_as_absent() -> None:
    submission = _submission(documents={"rne_extract": {"missing": True}})
    result = check_completeness(submission, today=TODAY)
    assert "rne_extract" in result.missing_documents


def test_missing_documents_are_labelled_bilingually() -> None:
    submission = _submission()
    del submission["documents"]["company_statutes"]

    payload = check_completeness(submission, today=TODAY).to_dict()
    entry = payload["missing_documents"][0]
    assert entry["key"] == "company_statutes"
    assert entry["label_fr"] and entry["label_ar"]


# ----------------------------------------------------- ID matching check

def test_mismatched_id_between_cin_and_pv_fails() -> None:
    submission = _submission(
        documents={
            "general_assembly_pv": {
                "fields": {
                    "decision_date": "2026-06-12",
                    "id_number": "87654321",
                    "person_name": "Amine Ben Salah",
                }
            }
        }
    )
    result = check_completeness(submission, today=TODAY)

    assert result.status is Status.NEEDS_REVIEW
    check = next(c for c in result.checks if c.name == "id_number_matches_across_documents")
    assert check.outcome is CheckOutcome.FAIL
    assert "12345678" in check.reason_fr and "87654321" in check.reason_fr
    assert check.evidence["conflicts"][0]["id_number"] == "87654321"


def test_id_comparison_ignores_spacing_and_punctuation() -> None:
    submission = _submission(
        documents={
            "general_assembly_pv": {
                "fields": {
                    "decision_date": "2026-06-12",
                    "id_number": "12 345 678",
                    "person_name": "Amine Ben Salah",
                }
            }
        }
    )
    result = check_completeness(submission, today=TODAY)
    assert _outcome(result, "id_number_matches_across_documents") is CheckOutcome.PASS


def test_secondary_id_numbers_are_also_compared() -> None:
    submission = _submission(
        documents={
            "general_assembly_pv": {
                "fields": {
                    "decision_date": "2026-06-12",
                    "id_number": "12345678",
                    "other_id_numbers": ["99999999"],
                    "person_name": "Amine Ben Salah",
                }
            }
        }
    )
    result = check_completeness(submission, today=TODAY)
    assert _outcome(result, "id_number_matches_across_documents") is CheckOutcome.FAIL


def test_unreadable_cin_is_indeterminate_not_a_failure() -> None:
    submission = _submission(
        documents={
            "id_new_representative": {
                "fields": {"id_number": None, "person_name": "Amine Ben Salah"}
            }
        }
    )
    result = check_completeness(submission, today=TODAY)
    assert _outcome(result, "id_number_matches_across_documents") is CheckOutcome.INDETERMINATE
    assert result.status is Status.NEEDS_REVIEW


# --------------------------------------------------- statutes name check

def test_statutes_not_naming_new_representative_fails() -> None:
    submission = _submission(
        documents={
            "company_statutes": {
                "fields": {"full_text": "Gérant: Slim Trabelsi, SARL Exemple Tunisie"}
            }
        }
    )
    result = check_completeness(submission, today=TODAY)
    check = next(
        c for c in result.checks if c.name == "statutes_reflect_new_representative_name"
    )
    assert check.outcome is CheckOutcome.FAIL
    assert "Amine Ben Salah" in check.reason_fr


def test_statutes_name_match_tolerates_reordering_and_case() -> None:
    submission = _submission(
        documents={
            "company_statutes": {
                "fields": {"full_text": "BEN SALAH, Amine — gérant unique"}
            }
        }
    )
    result = check_completeness(submission, today=TODAY)
    assert _outcome(result, "statutes_reflect_new_representative_name") is CheckOutcome.PASS


def test_empty_statutes_text_is_indeterminate() -> None:
    submission = _submission(documents={"company_statutes": {"fields": {}}})
    result = check_completeness(submission, today=TODAY)
    assert _outcome(result, "statutes_reflect_new_representative_name") is CheckOutcome.INDETERMINATE


# ------------------------------------------------------ extract age check

@pytest.mark.parametrize(
    ("age_days", "expected"),
    [
        (0, CheckOutcome.PASS),
        (RNE_EXTRACT_MAX_AGE_DAYS - 1, CheckOutcome.PASS),
        (RNE_EXTRACT_MAX_AGE_DAYS, CheckOutcome.PASS),      # boundary: 90 is OK
        (RNE_EXTRACT_MAX_AGE_DAYS + 1, CheckOutcome.FAIL),  # 91 is not
    ],
)
def test_extract_age_boundary(age_days: int, expected: CheckOutcome) -> None:
    issued = (TODAY - timedelta(days=age_days)).isoformat()
    submission = _submission(documents={"rne_extract": {"fields": {"issue_date": issued}}})
    result = check_completeness(submission, today=TODAY)
    assert _outcome(result, "rne_extract_not_older_than_90_days") is expected


def test_future_dated_extract_fails() -> None:
    submission = _submission(
        documents={"rne_extract": {"fields": {"issue_date": "2026-12-01"}}}
    )
    result = check_completeness(submission, today=TODAY)
    assert _outcome(result, "rne_extract_not_older_than_90_days") is CheckOutcome.FAIL


def test_missing_extract_date_is_indeterminate() -> None:
    submission = _submission(documents={"rne_extract": {"fields": {"issue_date": None}}})
    result = check_completeness(submission, today=TODAY)
    assert _outcome(result, "rne_extract_not_older_than_90_days") is CheckOutcome.INDETERMINATE


# --------------------------------------------------- filing deadline check

def _filed(decision: str, filed: str) -> CheckOutcome:
    submission = _submission(
        submitted_at=filed,
        documents={
            "general_assembly_pv": {
                "fields": {
                    "decision_date": decision,
                    "id_number": "12345678",
                    "person_name": "Amine Ben Salah",
                    "has_signature": True,
                    "signature_date": decision,
                }
            }
        },
    )
    result = check_completeness(submission, today=date.fromisoformat(filed))
    return _outcome(result, "filed_within_30_days_of_decision_date")


def test_deadline_is_one_month_not_thirty_days() -> None:
    """Article 26 says "un mois". One month from 31 January is 28 February --
    28 days -- so counting 30 would pass a filing that is already late."""
    assert _filed("2026-01-31", "2026-02-28") is CheckOutcome.PASS
    assert _filed("2026-01-31", "2026-03-01") is CheckOutcome.FAIL
    # Day 29 and day 30 after a 31 January decision are both late.
    assert _filed("2026-01-31", "2026-03-02") is CheckOutcome.FAIL


@pytest.mark.parametrize(
    ("decision", "filed", "expected"),
    [
        ("2026-06-15", "2026-06-15", CheckOutcome.PASS),  # same day
        ("2026-06-15", "2026-07-15", CheckOutcome.PASS),  # boundary: exactly one month
        ("2026-06-15", "2026-07-16", CheckOutcome.FAIL),  # a day past it
        ("2026-03-31", "2026-04-30", CheckOutcome.PASS),  # clamped to a valid day
        ("2026-03-31", "2026-05-01", CheckOutcome.FAIL),
    ],
)
def test_filing_deadline_boundary(decision: str, filed: str, expected: CheckOutcome) -> None:
    assert _filed(decision, filed) is expected


def test_deadline_constant_is_a_month() -> None:
    assert FILING_DEADLINE_MONTHS == 1


def _deadline_check(decision: str, filed: str = "2026-07-01"):
    submission = _submission(
        submitted_at=filed,
        documents={
            "general_assembly_pv": {
                "fields": {
                    "decision_date": decision,
                    "id_number": "12345678",
                    "person_name": "Amine Ben Salah",
                    "has_signature": True,
                    "signature_date": decision,
                }
            }
        },
    )
    return next(
        c
        for c in check_completeness(
            submission, today=date.fromisoformat(filed)
        ).checks
        if c.name == "filed_within_30_days_of_decision_date"
    )


def test_late_filing_reports_penalty_months_rounding_up() -> None:
    """Decision 21/05, deadline 21/06, filed 01/07 -- 10 days late, so one
    started month of penalty."""
    check = _deadline_check("2026-05-21")

    assert check.outcome is CheckOutcome.FAIL
    assert check.evidence["deadline"] == "2026-06-21"
    assert check.evidence["days_overdue"] == 10
    assert check.evidence["penalty_months"] == 1
    assert "52-2018" in check.reason_fr


def test_two_started_months_of_delay() -> None:
    """Decision 27/04, deadline 27/05, filed 01/07 -- 35 days late."""
    check = _deadline_check("2026-04-27")

    assert check.evidence["deadline"] == "2026-05-27"
    assert check.evidence["days_overdue"] == 35
    assert check.evidence["penalty_months"] == 2


def test_deadline_measured_from_submitted_at_not_today() -> None:
    """A filing deposited in time stays in time even when reviewed later."""
    submission = _submission(submitted_at="2026-06-20")  # decision 2026-06-12
    late_review_day = date(2026, 12, 31)
    result = check_completeness(submission, today=late_review_day)
    assert _outcome(result, "filed_within_30_days_of_decision_date") is CheckOutcome.PASS


@pytest.mark.parametrize("written", ["2026-06-12", "12/06/2026", "12-06-2026", "12.06.2026"])
def test_common_date_formats_are_accepted(written: str) -> None:
    submission = _submission(
        documents={
            "general_assembly_pv": {
                "fields": {
                    "decision_date": written,
                    "id_number": "12345678",
                    "person_name": "Amine Ben Salah",
                }
            }
        }
    )
    result = check_completeness(submission, today=TODAY)
    assert _outcome(result, "filed_within_30_days_of_decision_date") is CheckOutcome.PASS


def test_missing_decision_date_is_indeterminate() -> None:
    submission = _submission(
        documents={
            "general_assembly_pv": {
                "fields": {"id_number": "12345678", "person_name": "Amine Ben Salah"}
            }
        }
    )
    result = check_completeness(submission, today=TODAY)
    assert _outcome(result, "filed_within_30_days_of_decision_date") is CheckOutcome.INDETERMINATE


# ------------------------------------------------------------- aggregation

def test_missing_document_outranks_failed_check() -> None:
    """A filing that is both incomplete and inconsistent reads as INCOMPLETE."""
    submission = _submission(
        documents={
            "general_assembly_pv": {
                "fields": {
                    "decision_date": "2026-06-12",
                    "id_number": "87654321",
                    "person_name": "Amine Ben Salah",
                }
            }
        }
    )
    del submission["documents"]["tax_registration_card"]

    result = check_completeness(submission, today=TODAY)
    assert result.status is Status.INCOMPLETE
    assert result.failed_checks  # the mismatch is still reported


def test_result_serialises_for_the_api() -> None:
    payload = check_completeness(_submission(), today=TODAY).to_dict()
    assert payload["status"] == "COMPLETE"
    assert payload["official_reference"] == "RNE-M-005"
    assert payload["display_name_ar"] == "تحيين مؤسسة"
    assert len(payload["checks"]) == 5
    assert all(c["label_fr"] and c["label_ar"] for c in payload["checks"])


# ------------------------------------------------------- PV signature check

def test_signed_and_dated_pv_passes() -> None:
    result = check_completeness(_submission(), today=TODAY)
    assert _outcome(result, "pv_is_signed") is CheckOutcome.PASS


def test_missing_signature_date_fails() -> None:
    submission = _submission(
        documents={
            "general_assembly_pv": {
                "fields": {
                    "decision_date": "2026-06-12",
                    "id_number": "12345678",
                    "person_name": "Amine Ben Salah",
                    "has_signature": True,
                    "signature_date": None,
                }
            }
        }
    )
    result = check_completeness(submission, today=TODAY)
    check = next(c for c in result.checks if c.name == "pv_is_signed")
    assert check.outcome is CheckOutcome.FAIL
    assert "date de signature" in check.reason_fr
    assert result.status is Status.NEEDS_REVIEW


def test_unsigned_pv_fails() -> None:
    submission = _submission(
        documents={
            "general_assembly_pv": {
                "fields": {
                    "decision_date": "2026-06-12",
                    "id_number": "12345678",
                    "person_name": "Amine Ben Salah",
                    "has_signature": False,
                    "signature_date": None,
                }
            }
        }
    )
    result = check_completeness(submission, today=TODAY)
    assert _outcome(result, "pv_is_signed") is CheckOutcome.FAIL


def test_signature_predating_the_decision_fails() -> None:
    submission = _submission(
        documents={
            "general_assembly_pv": {
                "fields": {
                    "decision_date": "2026-06-12",
                    "id_number": "12345678",
                    "person_name": "Amine Ben Salah",
                    "has_signature": True,
                    "signature_date": "2026-06-01",
                }
            }
        }
    )
    result = check_completeness(submission, today=TODAY)
    assert _outcome(result, "pv_is_signed") is CheckOutcome.FAIL


def test_unreadable_signature_is_indeterminate_not_an_accusation() -> None:
    """OCR failing to see a signature must not read as 'you did not sign'."""
    submission = _submission(
        documents={
            "general_assembly_pv": {
                "fields": {
                    "decision_date": "2026-06-12",
                    "id_number": "12345678",
                    "person_name": "Amine Ben Salah",
                }
            }
        }
    )
    result = check_completeness(submission, today=TODAY)
    assert _outcome(result, "pv_is_signed") is CheckOutcome.INDETERMINATE


# ----------------------------------- company identifiers are not personal IDs

def test_company_identifier_in_statutes_is_not_a_cin_mismatch() -> None:
    """Statutes always carry the company's RNE id; it must not be compared
    against the representative's CIN. This fired on nearly every real filing."""
    submission = _submission(
        documents={
            "company_statutes": {
                "fields": {
                    "full_text": "Gérant: Amine Ben Salah",
                    "company_id": "8193319B",
                    "other_id_numbers": ["8193319B"],
                }
            }
        }
    )
    result = check_completeness(submission, today=TODAY)
    assert _outcome(result, "id_number_matches_across_documents") is CheckOutcome.PASS


def test_tax_identifier_variant_is_also_ignored() -> None:
    submission = _submission(
        documents={
            "company_statutes": {
                "fields": {
                    "full_text": "Gérant: Amine Ben Salah",
                    "company_id": "8193319B",
                    "other_id_numbers": ["8193319BA/M000"],
                }
            }
        }
    )
    result = check_completeness(submission, today=TODAY)
    assert _outcome(result, "id_number_matches_across_documents") is CheckOutcome.PASS


def test_non_cin_shaped_number_is_ignored() -> None:
    """Seven digits is not a CIN; only 8-digit values are comparable."""
    submission = _submission(
        documents={
            "general_assembly_pv": {
                "fields": {
                    "decision_date": "2026-06-12",
                    "id_number": "12345678",
                    "other_id_numbers": ["1234567"],
                    "person_name": "Amine Ben Salah",
                    "has_signature": True,
                    "signature_date": "2026-06-12",
                }
            }
        }
    )
    result = check_completeness(submission, today=TODAY)
    assert _outcome(result, "id_number_matches_across_documents") is CheckOutcome.PASS


def test_a_genuine_second_cin_still_fails() -> None:
    """The narrowing must not blind the check to a real mismatch."""
    submission = _submission(
        documents={
            "general_assembly_pv": {
                "fields": {
                    "decision_date": "2026-06-12",
                    "id_number": "12345678",
                    "other_id_numbers": ["87654321"],
                    "person_name": "Amine Ben Salah",
                    "has_signature": True,
                    "signature_date": "2026-06-12",
                }
            }
        }
    )
    result = check_completeness(submission, today=TODAY)
    assert _outcome(result, "id_number_matches_across_documents") is CheckOutcome.FAIL
