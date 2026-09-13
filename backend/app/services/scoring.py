"""Cross-document inconsistency flagging for the officer dashboard.

Turns the rules engine's machine-readable check results into concrete,
human-readable flags an officer can act on without opening every document --
"ID number on national ID (12345678) does not match ID number referenced in PV
(87654321)" rather than "check failed".

This module deliberately adds NO new rules. The checks it reports are exactly
the ones declared in rules_engine.TRANSACTION_RULES, so there is one source of
truth for what "wrong" means and the dashboard can never disagree with the
completeness result shown to the MSME.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any

from app.services.rules_engine import (
    DOCUMENT_LABELS,
    CheckOutcome,
    CheckResult,
    CompletenessResult,
    check_completeness,
)


class Severity(str, Enum):
    # Blocks the filing: a rule was definitively violated.
    ERROR = "ERROR"
    # Needs a human: we could not read enough to decide.
    WARNING = "WARNING"
    # Worth knowing, blocks nothing.
    INFO = "INFO"


# Which document a given check's evidence points at, so the dashboard can jump
# straight to the page that needs looking at.
_CHECK_FOCUS: dict[str, str] = {
    # No single document: the finding names whichever pages are wrong, and the
    # flag's own documents list carries them.
    "id_number_matches_across_documents": "id_new_representative",
    "statutes_reflect_new_representative_name": "company_statutes",
    "rne_extract_not_older_than_90_days": "rne_extract",
    "filed_within_legal_deadline_of_decision_date": "general_assembly_pv",
    "pv_is_signed": "general_assembly_pv",
    "financial_statements_signed_and_stamped": "financial_statements_signed",
    "pv_registered_with_recette_des_finances_if_applicable": "general_assembly_pv_approval",
    "auditor_report_present_if_required_by_company_type": "auditor_report",
    "shareholder_list_ids_present_for_each_entry": "updated_shareholder_list",
    "filed_within_7_months_of_fiscal_year_close": "financial_statements_signed",
}

# Default when a caller passes a bare document mapping with no transaction type.
DEFAULT_TRANSACTION_TYPE = "RNE_MODIFICATION_ENTREPRISE"


@dataclass
class Flag:
    """One actionable finding for the officer queue."""

    code: str
    severity: Severity
    message_fr: str
    message_ar: str
    documents: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "message_fr": self.message_fr,
            "message_ar": self.message_ar,
            "documents": [
                {
                    "key": key,
                    "label_fr": DOCUMENT_LABELS.get(key, {}).get("fr", key),
                    "label_ar": DOCUMENT_LABELS.get(key, {}).get("ar", key),
                }
                for key in self.documents
            ],
            "evidence": self.evidence,
        }


def flag_inconsistencies(
    extracted_fields: dict[str, Any],
    today: date | None = None,
    transaction_type: str | None = None,
) -> list[Flag]:
    """Run the declared cross-document checks and return readable flags.

    Works for any transaction in TRANSACTION_RULES: the checks come from the
    rules engine, so adding a workflow there adds it here with no change.

    Accepts either a full submission dict (``{"transaction_type": ...,
    "documents": {...}}``) or a bare mapping of document key -> extracted
    fields, which is what the OCR stage produces. `transaction_type` names the
    workflow when the input is a bare mapping.

    Returns ERROR flags first, then WARNING, then INFO; within a severity the
    rules engine's declaration order is preserved so the display is stable.
    """
    submission = _as_submission(extracted_fields, transaction_type)
    result = check_completeness(submission, today=today)
    return flags_from_result(result)


def flags_from_result(result: CompletenessResult) -> list[Flag]:
    """Build flags from an already-computed completeness result.

    Used by the API so a submission is validated once, not twice.
    """
    flags = [_flag_missing_document(key) for key in result.missing_documents]
    flags += [
        flag
        for check in result.checks
        if (flag := _flag_from_check(check)) is not None
    ]

    order = {Severity.ERROR: 0, Severity.WARNING: 1, Severity.INFO: 2}
    return sorted(flags, key=lambda flag: order[flag.severity])


# --------------------------------------------------------------- conversion

def _flag_missing_document(key: str) -> Flag:
    labels = DOCUMENT_LABELS.get(key, {})
    label_fr = labels.get("fr", key)
    label_ar = labels.get("ar", key)
    return Flag(
        code="missing_document",
        severity=Severity.ERROR,
        message_fr=f"Document manquant : {label_fr}.",
        message_ar=f"وثيقة ناقصة: {label_ar}.",
        documents=[key],
        evidence={"document": key},
    )


def _flag_from_check(check: CheckResult) -> Flag | None:
    """A passing check produces no flag; the dashboard only shows problems."""
    if check.outcome is CheckOutcome.PASS:
        return None

    severity = (
        Severity.ERROR if check.outcome is CheckOutcome.FAIL else Severity.WARNING
    )
    documents = _documents_for(check)

    return Flag(
        code=check.name,
        severity=severity,
        message_fr=check.reason_fr or check.label_fr,
        message_ar=check.reason_ar or check.label_ar,
        documents=documents,
        evidence=check.evidence,
    )


def _documents_for(check: CheckResult) -> list[str]:
    """Documents an officer should open for this check, most relevant first."""
    focus = _CHECK_FOCUS.get(check.name)
    documents = [focus] if focus else []

    # An ID mismatch implicates whichever document carried the conflicting
    # number, so the officer can compare the two side by side.
    for conflict in check.evidence.get("conflicts", []):
        source = conflict.get("document")
        if source and source not in documents:
            documents.append(source)

    return documents


def _as_submission(
    extracted_fields: dict[str, Any], transaction_type: str | None = None
) -> dict[str, Any]:
    """Normalise either accepted input shape into a submission dict."""
    fallback = transaction_type or DEFAULT_TRANSACTION_TYPE

    if "documents" in extracted_fields or "transaction_type" in extracted_fields:
        submission = dict(extracted_fields)
        submission.setdefault("transaction_type", fallback)
        submission.setdefault("documents", {})
        return submission

    return {"transaction_type": fallback, "documents": extracted_fields}


# ------------------------------------------------------------------ summary

def flag_summary(flags: list[Flag]) -> dict[str, int]:
    """Counts per severity, for the queue's flag badge."""
    return {
        "total": len(flags),
        "errors": sum(1 for f in flags if f.severity is Severity.ERROR),
        "warnings": sum(1 for f in flags if f.severity is Severity.WARNING),
        "info": sum(1 for f in flags if f.severity is Severity.INFO),
    }
