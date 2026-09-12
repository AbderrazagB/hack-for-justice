"""Rules for the annual financial statements filing.

The second workflow shares every mechanism with the first; these tests pin what
is specific to it -- the conditional auditor report, the seven-month deadline
and its penalty arithmetic, and the shareholder identity cross-reference.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.services.rules_engine import (
    FINANCIAL_FILING_DEADLINE_MONTHS,
    PENALTY_TND_PER_MONTH_INDIVIDUAL,
    PENALTY_TND_PER_MONTH_LEGAL_ENTITY,
    TRANSACTION_RULES,
    CheckOutcome,
    Status,
    _add_months,
    auditor_report_required,
    check_completeness,
    required_documents_for,
)
from app.services.scoring import flag_inconsistencies

TXN = "RNE_FINANCIAL_STATEMENTS"
TODAY = date(2026, 7, 1)


def _submission(**overrides):
    documents = {
        "financial_statements_signed": {
            "fields": {"has_signature": True, "has_stamp": True}
        },
        "general_assembly_pv_approval": {
            "fields": {
                "full_text": "Assemblée générale ordinaire",
                "registration_reference": "RF-2026-0042",
            }
        },
        "auditor_report": {"fields": {"full_text": "Rapport du commissaire"}},
        "updated_shareholder_list": {
            "fields": {
                "shareholders": [
                    {"name": "Amine Ben Salah", "id_number": "12345678"},
                    {"name": "Salma Trabelsi", "id_number": "87654321"},
                ]
            }
        },
    }
    documents.update(overrides.pop("documents", {}))

    submission = {
        "transaction_type": TXN,
        "company_type": "SA",
        "fiscal_year_end": "2025-12-31",
        "submitted_at": "2026-07-01",
        "documents": documents,
    }
    submission.update(overrides)
    return submission


def _outcome(result, name) -> CheckOutcome:
    return next(c for c in result.checks if c.name == name).outcome


# ----------------------------------------------------------- rule definition

def test_transaction_is_registered_alongside_the_first_workflow() -> None:
    assert "RNE_MODIFICATION_ENTREPRISE" in TRANSACTION_RULES
    rules = TRANSACTION_RULES[TXN]
    assert rules["display_name_fr"] == "Dépôt des États Financiers Annuels"
    assert rules["display_name_ar"] == "إيداع القوائم المالية السنوية"
    assert rules["required_documents"] == [
        "financial_statements_signed",
        "general_assembly_pv_approval",
        "auditor_report",
        "updated_shareholder_list",
    ]
    assert rules["checks"] == [
        "financial_statements_signed_and_stamped",
        "pv_registered_with_recette_des_finances_if_applicable",
        "auditor_report_present_if_required_by_company_type",
        "shareholder_list_ids_present_for_each_entry",
        "filed_within_7_months_of_fiscal_year_close",
        "declaration_matches_documents",
    ]


def test_clean_filing_is_complete() -> None:
    result = check_completeness(_submission(), today=TODAY)
    assert result.status is Status.COMPLETE
    assert result.missing_documents == []


# ------------------------------------------------------- signature and stamp

def test_missing_stamp_fails() -> None:
    submission = _submission(
        documents={
            "financial_statements_signed": {
                "fields": {"has_signature": True, "has_stamp": False}
            }
        }
    )
    result = check_completeness(submission, today=TODAY)
    assert _outcome(result, "financial_statements_signed_and_stamped") is CheckOutcome.FAIL


def test_unreadable_statements_are_indeterminate() -> None:
    submission = _submission(
        documents={"financial_statements_signed": {"fields": {}}}
    )
    result = check_completeness(submission, today=TODAY)
    assert _outcome(result, "financial_statements_signed_and_stamped") is CheckOutcome.INDETERMINATE


def test_signature_can_be_inferred_from_text() -> None:
    submission = _submission(
        documents={
            "financial_statements_signed": {
                "fields": {"full_text": "Signature du gérant — cachet de la société"}
            }
        }
    )
    result = check_completeness(submission, today=TODAY)
    assert _outcome(result, "financial_statements_signed_and_stamped") is CheckOutcome.PASS


# ------------------------------------------------- recette des finances (PV)

def test_registration_reference_passes() -> None:
    result = check_completeness(_submission(), today=TODAY)
    assert _outcome(result, "pv_registered_with_recette_des_finances_if_applicable") is CheckOutcome.PASS


def test_unconfirmed_registration_goes_to_review_never_rejects() -> None:
    """Whether registration is owed is a legal reading, so this must not fail."""
    submission = _submission(
        documents={
            "general_assembly_pv_approval": {
                "fields": {"full_text": "Procès-verbal de l'assemblée"}
            }
        }
    )
    result = check_completeness(submission, today=TODAY)
    check = next(
        c
        for c in result.checks
        if c.name == "pv_registered_with_recette_des_finances_if_applicable"
    )
    assert check.outcome is CheckOutcome.INDETERMINATE
    assert check.outcome is not CheckOutcome.FAIL
    assert result.status is Status.NEEDS_REVIEW


# ----------------------------------------------------------- auditor report

@pytest.mark.parametrize("company_type", ["SA", "SCA"])
def test_auditor_report_is_required_for_share_companies(company_type: str) -> None:
    assert auditor_report_required({"company_type": company_type}) is True


@pytest.mark.parametrize("company_type", ["SARL", "SUARL", "SNC", "PERSONNE_PHYSIQUE"])
def test_auditor_report_is_not_required_by_default(company_type: str) -> None:
    assert auditor_report_required({"company_type": company_type}) is False


def test_sarl_over_thresholds_declares_an_auditor_is_required() -> None:
    assert auditor_report_required({"company_type": "SARL", "auditor_required": True}) is True


def test_missing_auditor_report_fails_for_an_sa() -> None:
    submission = _submission(company_type="SA")
    del submission["documents"]["auditor_report"]

    result = check_completeness(submission, today=TODAY)
    assert _outcome(result, "auditor_report_present_if_required_by_company_type") is CheckOutcome.FAIL
    assert "auditor_report" in result.missing_documents


def test_absent_auditor_report_is_not_missing_for_a_sarl() -> None:
    """It must not be listed as a missing document when it is not owed."""
    submission = _submission(company_type="SARL")
    del submission["documents"]["auditor_report"]

    result = check_completeness(submission, today=TODAY)
    assert "auditor_report" not in result.missing_documents
    assert _outcome(result, "auditor_report_present_if_required_by_company_type") is CheckOutcome.PASS
    assert result.status is Status.COMPLETE


def test_required_documents_drop_the_auditor_report_when_not_owed() -> None:
    rules = TRANSACTION_RULES[TXN]
    assert "auditor_report" in required_documents_for(rules, {"company_type": "SA"})
    assert "auditor_report" not in required_documents_for(rules, {"company_type": "SARL"})


def test_unknown_company_type_is_indeterminate() -> None:
    submission = _submission(company_type="")
    result = check_completeness(submission, today=TODAY)
    assert _outcome(result, "auditor_report_present_if_required_by_company_type") is CheckOutcome.INDETERMINATE


# ------------------------------------------------------- shareholder list

def test_shareholder_without_id_fails_and_is_named() -> None:
    submission = _submission(
        documents={
            "updated_shareholder_list": {
                "fields": {
                    "shareholders": [
                        {"name": "Amine Ben Salah", "id_number": "12345678"},
                        {"name": "Salma Trabelsi", "id_number": None},
                    ]
                }
            }
        }
    )
    result = check_completeness(submission, today=TODAY)
    check = next(
        c for c in result.checks if c.name == "shareholder_list_ids_present_for_each_entry"
    )
    assert check.outcome is CheckOutcome.FAIL
    assert "Salma Trabelsi" in check.reason_fr
    assert check.evidence["missing_ids"] == 1


def test_unreadable_shareholder_list_is_indeterminate() -> None:
    submission = _submission(
        documents={"updated_shareholder_list": {"fields": {"shareholders": []}}}
    )
    result = check_completeness(submission, today=TODAY)
    assert _outcome(result, "shareholder_list_ids_present_for_each_entry") is CheckOutcome.INDETERMINATE


# ---------------------------------------------------------------- deadline

def test_seven_month_deadline_boundary() -> None:
    """A 31 December close is due 31 July; the 31st itself is still in time."""
    on_time = _submission(fiscal_year_end="2025-12-31", submitted_at="2026-07-31")
    late = _submission(fiscal_year_end="2025-12-31", submitted_at="2026-08-01")

    assert _outcome(check_completeness(on_time, today=date(2026, 7, 31)),
                    "filed_within_7_months_of_fiscal_year_close") is CheckOutcome.PASS
    assert _outcome(check_completeness(late, today=date(2026, 8, 1)),
                    "filed_within_7_months_of_fiscal_year_close") is CheckOutcome.FAIL


def test_late_filing_computes_the_legal_entity_penalty() -> None:
    submission = _submission(
        company_type="SA", fiscal_year_end="2025-12-31", submitted_at="2026-10-15"
    )
    check = next(
        c
        for c in check_completeness(submission, today=date(2026, 10, 15)).checks
        if c.name == "filed_within_7_months_of_fiscal_year_close"
    )
    assert check.evidence["days_overdue"] == 76
    assert check.evidence["penalty_months"] == 3
    assert check.evidence["penalty_rate_tnd"] == PENALTY_TND_PER_MONTH_LEGAL_ENTITY
    assert check.evidence["penalty_total_tnd"] == 75


def test_individuals_pay_the_lower_rate() -> None:
    submission = _submission(
        company_type="PERSONNE_PHYSIQUE",
        fiscal_year_end="2025-12-31",
        submitted_at="2026-10-15",
    )
    check = next(
        c
        for c in check_completeness(submission, today=date(2026, 10, 15)).checks
        if c.name == "filed_within_7_months_of_fiscal_year_close"
    )
    assert check.evidence["penalty_rate_tnd"] == PENALTY_TND_PER_MONTH_INDIVIDUAL
    assert check.evidence["penalty_total_tnd"] == 30


def test_missing_fiscal_year_end_is_indeterminate() -> None:
    submission = _submission(fiscal_year_end=None)
    result = check_completeness(submission, today=TODAY)
    assert _outcome(result, "filed_within_7_months_of_fiscal_year_close") is CheckOutcome.INDETERMINATE


@pytest.mark.parametrize(
    ("close", "expected"),
    [
        (date(2025, 12, 31), date(2026, 7, 31)),
        (date(2026, 1, 31), date(2026, 8, 31)),
        (date(2026, 7, 31), date(2027, 2, 28)),  # clamped, February has no 31st
        (date(2026, 6, 30), date(2027, 1, 30)),
    ],
)
def test_month_arithmetic_clamps_to_a_valid_day(close: date, expected: date) -> None:
    assert _add_months(close, FINANCIAL_FILING_DEADLINE_MONTHS) == expected


# ------------------------------------------------------------------- flags

def test_flags_generalise_to_this_workflow() -> None:
    submission = _submission(
        company_type="SA", fiscal_year_end="2025-12-31", submitted_at="2026-10-15"
    )
    del submission["documents"]["auditor_report"]

    codes = {f.code for f in flag_inconsistencies(submission, today=date(2026, 10, 15))}
    assert "auditor_report_present_if_required_by_company_type" in codes
    assert "filed_within_7_months_of_fiscal_year_close" in codes
    assert "missing_document" in codes


def test_penalty_appears_in_the_flag_message() -> None:
    submission = _submission(
        company_type="SA", fiscal_year_end="2025-12-31", submitted_at="2026-10-15"
    )
    flag = next(
        f
        for f in flag_inconsistencies(submission, today=date(2026, 10, 15))
        if f.code == "filed_within_7_months_of_fiscal_year_close"
    )
    assert "25 DT/mois" in flag.message_fr
    assert "personnes morales" in flag.message_fr


def test_flags_point_at_the_right_documents() -> None:
    submission = _submission(
        documents={
            "updated_shareholder_list": {
                "fields": {"shareholders": [{"name": "X", "id_number": None}]}
            }
        }
    )
    flag = next(
        f
        for f in flag_inconsistencies(submission, today=TODAY)
        if f.code == "shareholder_list_ids_present_for_each_entry"
    )
    # Flag.documents holds raw keys; to_dict() is what labels them.
    assert flag.documents[0] == "updated_shareholder_list"
    assert flag.to_dict()["documents"][0]["label_fr"] == (
        "Liste actualisée des actionnaires/associés"
    )


# ------------------------------- AGO minutes are conditional, not mandatory

def test_ago_minutes_are_required_by_default() -> None:
    submission = _submission()
    del submission["documents"]["general_assembly_pv_approval"]

    result = check_completeness(submission, today=TODAY)
    assert "general_assembly_pv_approval" in result.missing_documents


def test_statements_may_be_filed_before_the_assembly_has_met() -> None:
    """The RNE permits filing the statements alone before the deadline and
    completing the rest later, so an early filer is not incomplete."""
    submission = _submission(ago_not_held=True)
    del submission["documents"]["general_assembly_pv_approval"]

    result = check_completeness(submission, today=TODAY)
    assert result.status is Status.COMPLETE
    assert "general_assembly_pv_approval" not in result.missing_documents


def test_registration_check_passes_when_the_assembly_has_not_met() -> None:
    submission = _submission(ago_not_held=True)
    del submission["documents"]["general_assembly_pv_approval"]

    result = check_completeness(submission, today=TODAY)
    assert _outcome(
        result, "pv_registered_with_recette_des_finances_if_applicable"
    ) is CheckOutcome.PASS


def test_required_documents_drop_the_minutes_when_the_assembly_has_not_met() -> None:
    rules = TRANSACTION_RULES[TXN]
    assert "general_assembly_pv_approval" in required_documents_for(rules, {})
    assert "general_assembly_pv_approval" not in required_documents_for(
        rules, {"ago_not_held": True}
    )
