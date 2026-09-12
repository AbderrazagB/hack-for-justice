"""Deterministic completeness rules for RNE transactions.

TRANSACTION_RULES below is the SINGLE SOURCE OF TRUTH for what "complete" means.
The LLM is never asked whether a filing is complete -- it only explains results
this module produced. Keeping the rules deterministic means an officer can
always be told exactly which rule fired and why, and the answer never changes
between two runs on the same submission.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any

# ---------------------------------------------------------------------------
# Rule definitions
# ---------------------------------------------------------------------------

TRANSACTION_RULES = {
    "RNE_MODIFICATION_ENTREPRISE": {
        "display_name_fr": "Modification Entreprise",
        "display_name_ar": "تحيين مؤسسة",
        "official_reference": "RNE-M-005",
        "required_documents": [
            "id_new_representative",
            "company_statutes",
            "rne_extract",
            "tax_registration_card",
            "general_assembly_pv",
        ],
        "checks": [
            "id_number_matches_across_documents",
            "statutes_reflect_new_representative_name",
            "rne_extract_not_older_than_90_days",
            "filed_within_30_days_of_decision_date",
        ],
    },
}

# Human-readable labels for the UI. Keyed by the identifiers above.
DOCUMENT_LABELS: dict[str, dict[str, str]] = {
    "id_new_representative": {
        "fr": "Carte d'identité nationale du nouveau représentant",
        "ar": "بطاقة التعريف الوطنية للممثل الجديد",
    },
    "company_statutes": {
        "fr": "Statuts mis à jour de la société",
        "ar": "النظام الأساسي المحيّن للشركة",
    },
    "rne_extract": {"fr": "Extrait RNE en cours", "ar": "مضمون السجل الوطني للمؤسسات"},
    "tax_registration_card": {
        "fr": "Carte d'identification fiscale (déclaration d'existence)",
        "ar": "بطاقة التعريف الجبائي (التصريح بالوجود)",
    },
    "general_assembly_pv": {
        "fr": "Procès-verbal de l'assemblée générale",
        "ar": "محضر الجلسة العامة",
    },
}

CHECK_LABELS: dict[str, dict[str, str]] = {
    "id_number_matches_across_documents": {
        "fr": "Le numéro de CIN concorde entre les documents",
        "ar": "تطابق رقم بطاقة التعريف بين الوثائق",
    },
    "statutes_reflect_new_representative_name": {
        "fr": "Les statuts mentionnent le nouveau représentant",
        "ar": "النظام الأساسي يذكر الممثل الجديد",
    },
    "rne_extract_not_older_than_90_days": {
        "fr": "L'Extrait RNE date de moins de 90 jours",
        "ar": "مضمون السجل أقل من 90 يوماً",
    },
    "filed_within_30_days_of_decision_date": {
        "fr": "Dépôt dans les 30 jours suivant la décision",
        "ar": "الإيداع في أجل 30 يوماً من تاريخ القرار",
    },
}

# The Extrait RNE must be recent. Not a statutory figure from Law 52-2018 -- it
# is the registry's practical freshness expectation, kept here (not in the RAG
# corpus) precisely so it is not presented to users as if it were law.
RNE_EXTRACT_MAX_AGE_DAYS = 90

# Statutory: Law 52-2018 relating to the RNE. Mirrors the seeded corpus entry.
FILING_DEADLINE_DAYS = 30


class Status(str, Enum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class CheckOutcome(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    # Ran, but the inputs were missing or unreadable -- a human must look.
    INDETERMINATE = "INDETERMINATE"


@dataclass
class CheckResult:
    name: str
    outcome: CheckOutcome
    reason_fr: str = ""
    reason_ar: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def label_fr(self) -> str:
        return CHECK_LABELS.get(self.name, {}).get("fr", self.name)

    @property
    def label_ar(self) -> str:
        return CHECK_LABELS.get(self.name, {}).get("ar", self.name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "outcome": self.outcome.value,
            "label_fr": self.label_fr,
            "label_ar": self.label_ar,
            "reason_fr": self.reason_fr,
            "reason_ar": self.reason_ar,
            "evidence": self.evidence,
        }


@dataclass
class CompletenessResult:
    transaction_type: str
    status: Status
    missing_documents: list[str] = field(default_factory=list)
    present_documents: list[str] = field(default_factory=list)
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def failed_checks(self) -> list[CheckResult]:
        return [c for c in self.checks if c.outcome is CheckOutcome.FAIL]

    @property
    def indeterminate_checks(self) -> list[CheckResult]:
        return [c for c in self.checks if c.outcome is CheckOutcome.INDETERMINATE]

    def to_dict(self) -> dict[str, Any]:
        rules = TRANSACTION_RULES.get(self.transaction_type, {})
        return {
            "transaction_type": self.transaction_type,
            "display_name_fr": rules.get("display_name_fr", ""),
            "display_name_ar": rules.get("display_name_ar", ""),
            "official_reference": rules.get("official_reference", ""),
            "status": self.status.value,
            "missing_documents": [
                {
                    "key": key,
                    "label_fr": DOCUMENT_LABELS.get(key, {}).get("fr", key),
                    "label_ar": DOCUMENT_LABELS.get(key, {}).get("ar", key),
                }
                for key in self.missing_documents
            ],
            "present_documents": self.present_documents,
            "checks": [check.to_dict() for check in self.checks],
        }


class UnknownTransactionType(ValueError):
    """Raised for a transaction type not defined in TRANSACTION_RULES."""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def check_completeness(
    submission: dict[str, Any], today: date | None = None
) -> CompletenessResult:
    """Validate one submission against its transaction's rules.

    `submission` is expected to look like::

        {
          "transaction_type": "RNE_MODIFICATION_ENTREPRISE",
          "documents": {
             "id_new_representative": {"fields": {"id_number": "12345678", ...}},
             ...
          },
          "submitted_at": "2026-07-10",   # optional, defaults to today
        }

    `today` is injectable so date-sensitive rules are testable.
    """
    transaction_type = submission.get("transaction_type", "")
    rules = TRANSACTION_RULES.get(transaction_type)
    if rules is None:
        raise UnknownTransactionType(
            f"Unknown transaction type {transaction_type!r}. "
            f"Known: {', '.join(TRANSACTION_RULES)}"
        )

    today = today or date.today()
    documents: dict[str, Any] = submission.get("documents") or {}

    present = [key for key in rules["required_documents"] if _has_document(documents, key)]
    missing = [key for key in rules["required_documents"] if key not in present]

    checks = [
        _CHECK_IMPLEMENTATIONS[name](documents, submission, today)
        for name in rules["checks"]
    ]

    if missing:
        status = Status.INCOMPLETE
    elif any(c.outcome is CheckOutcome.FAIL for c in checks):
        status = Status.NEEDS_REVIEW
    elif any(c.outcome is CheckOutcome.INDETERMINATE for c in checks):
        status = Status.NEEDS_REVIEW
    else:
        status = Status.COMPLETE

    return CompletenessResult(
        transaction_type=transaction_type,
        status=status,
        missing_documents=missing,
        present_documents=present,
        checks=checks,
    )


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def _check_id_number_matches(
    documents: dict[str, Any], submission: dict[str, Any], today: date
) -> CheckResult:
    """Compare the CIN on the national ID against IDs cited elsewhere.

    The national ID is authoritative. Any ID number appearing in the PV or the
    statutes must either match it or be absent -- a different number means the
    paperwork names a different person.
    """
    name = "id_number_matches_across_documents"
    reference = _normalise_id(_field(documents, "id_new_representative", "id_number"))

    if not reference:
        return CheckResult(
            name,
            CheckOutcome.INDETERMINATE,
            "Numéro de CIN illisible ou absent de la carte d'identité.",
            "رقم بطاقة التعريف غير مقروء أو غير موجود.",
        )

    conflicts: list[dict[str, str]] = []
    for doc_key in ("general_assembly_pv", "company_statutes"):
        for candidate in _all_ids(documents, doc_key):
            if candidate != reference:
                conflicts.append({"document": doc_key, "id_number": candidate})

    if conflicts:
        listed = ", ".join(f"{c['id_number']} ({c['document']})" for c in conflicts)
        return CheckResult(
            name,
            CheckOutcome.FAIL,
            f"Le numéro de CIN de la carte d'identité ({reference}) ne correspond "
            f"pas au(x) numéro(s) cité(s) ailleurs : {listed}.",
            f"رقم بطاقة التعريف ({reference}) لا يطابق الرقم المذكور في وثائق أخرى: {listed}.",
            {"reference_id": reference, "conflicts": conflicts},
        )

    return CheckResult(
        name,
        CheckOutcome.PASS,
        f"Le numéro de CIN ({reference}) concorde entre les documents.",
        f"رقم بطاقة التعريف ({reference}) متطابق بين الوثائق.",
        {"reference_id": reference},
    )


def _check_statutes_name(
    documents: dict[str, Any], submission: dict[str, Any], today: date
) -> CheckResult:
    """The updated statutes must actually name the incoming representative."""
    name = "statutes_reflect_new_representative_name"
    person = _field(documents, "id_new_representative", "person_name") or _field(
        documents, "general_assembly_pv", "person_name"
    )
    statutes = documents.get("company_statutes") or {}
    haystack = " ".join(
        str(value)
        for value in [
            (statutes.get("fields") or {}).get("full_text"),
            (statutes.get("fields") or {}).get("person_name"),
            statutes.get("full_text"),
        ]
        if value
    )

    if not person or not haystack.strip():
        return CheckResult(
            name,
            CheckOutcome.INDETERMINATE,
            "Impossible de comparer : nom du représentant ou texte des statuts absent.",
            "تعذّرت المقارنة: اسم الممثل أو نص النظام الأساسي غير متوفر.",
        )

    if _name_present(person, haystack):
        return CheckResult(
            name,
            CheckOutcome.PASS,
            f"Les statuts mentionnent bien {person}.",
            f"النظام الأساسي يذكر {person}.",
            {"person_name": person},
        )

    return CheckResult(
        name,
        CheckOutcome.FAIL,
        f"Les statuts fournis ne mentionnent pas le nouveau représentant {person}. "
        "Des statuts mis à jour sont requis.",
        f"النظام الأساسي المقدَّم لا يذكر الممثل الجديد {person}. يجب تقديم نظام أساسي محيّن.",
        {"person_name": person},
    )


def _check_extract_age(
    documents: dict[str, Any], submission: dict[str, Any], today: date
) -> CheckResult:
    """The Extrait RNE must be recent enough to reflect current registry state."""
    name = "rne_extract_not_older_than_90_days"
    issued = _parse_date(_field(documents, "rne_extract", "issue_date"))

    if issued is None:
        return CheckResult(
            name,
            CheckOutcome.INDETERMINATE,
            "Date de délivrance de l'Extrait RNE illisible ou absente.",
            "تاريخ إصدار مضمون السجل غير مقروء أو غير موجود.",
        )

    age = (today - issued).days
    evidence = {"issue_date": issued.isoformat(), "age_days": age}

    if age > RNE_EXTRACT_MAX_AGE_DAYS:
        return CheckResult(
            name,
            CheckOutcome.FAIL,
            f"L'Extrait RNE date du {issued:%d/%m/%Y}, soit {age} jours "
            f"(maximum {RNE_EXTRACT_MAX_AGE_DAYS}). Un extrait récent est requis.",
            f"مضمون السجل مؤرخ في {issued:%d/%m/%Y} أي منذ {age} يوماً "
            f"(الأقصى {RNE_EXTRACT_MAX_AGE_DAYS}). يلزم مضمون حديث.",
            evidence,
        )

    if age < 0:
        return CheckResult(
            name,
            CheckOutcome.FAIL,
            f"L'Extrait RNE porte une date future ({issued:%d/%m/%Y}).",
            f"مضمون السجل يحمل تاريخاً مستقبلياً ({issued:%d/%m/%Y}).",
            evidence,
        )

    return CheckResult(
        name,
        CheckOutcome.PASS,
        f"L'Extrait RNE date de {age} jours.",
        f"مضمون السجل عمره {age} يوماً.",
        evidence,
    )


def _check_filing_deadline(
    documents: dict[str, Any], submission: dict[str, Any], today: date
) -> CheckResult:
    """Law 52-2018: file within 30 days of the triggering decision."""
    name = "filed_within_30_days_of_decision_date"
    decision = _parse_date(_field(documents, "general_assembly_pv", "decision_date"))
    filed = _parse_date(submission.get("submitted_at")) or today

    if decision is None:
        return CheckResult(
            name,
            CheckOutcome.INDETERMINATE,
            "Date de la décision illisible ou absente du procès-verbal.",
            "تاريخ القرار غير مقروء أو غير موجود بالمحضر.",
        )

    elapsed = (filed - decision).days
    evidence = {
        "decision_date": decision.isoformat(),
        "filed_date": filed.isoformat(),
        "elapsed_days": elapsed,
        "deadline_days": FILING_DEADLINE_DAYS,
    }

    if elapsed < 0:
        return CheckResult(
            name,
            CheckOutcome.FAIL,
            f"La date de décision ({decision:%d/%m/%Y}) est postérieure au dépôt.",
            f"تاريخ القرار ({decision:%d/%m/%Y}) لاحق لتاريخ الإيداع.",
            evidence,
        )

    if elapsed > FILING_DEADLINE_DAYS:
        # Penalty mirrors the seeded corpus entry: half the standard fee per
        # month or fraction of a month of delay.
        overdue = elapsed - FILING_DEADLINE_DAYS
        months = -(-overdue // 30)  # ceil: any fraction counts as a whole month
        evidence |= {"days_overdue": overdue, "penalty_months": months}
        return CheckResult(
            name,
            CheckOutcome.FAIL,
            f"Dépôt hors délai : {elapsed} jours après la décision du "
            f"{decision:%d/%m/%Y} (limite {FILING_DEADLINE_DAYS} jours, "
            f"loi 52-2018). Retard de {overdue} jours, soit une pénalité de "
            f"{months} mois entamé(s).",
            f"إيداع خارج الأجل: {elapsed} يوماً بعد قرار {decision:%d/%m/%Y} "
            f"(الأجل {FILING_DEADLINE_DAYS} يوماً، القانون 52-2018). "
            f"تأخير {overdue} يوماً أي خطية عن {months} شهراً.",
            evidence,
        )

    return CheckResult(
        name,
        CheckOutcome.PASS,
        f"Déposé {elapsed} jours après la décision (limite {FILING_DEADLINE_DAYS}).",
        f"تم الإيداع بعد {elapsed} يوماً من القرار (الأجل {FILING_DEADLINE_DAYS}).",
        evidence,
    )


_CHECK_IMPLEMENTATIONS = {
    "id_number_matches_across_documents": _check_id_number_matches,
    "statutes_reflect_new_representative_name": _check_statutes_name,
    "rne_extract_not_older_than_90_days": _check_extract_age,
    "filed_within_30_days_of_decision_date": _check_filing_deadline,
}

# Fail loudly at import time if a rule names a check nobody implemented.
for _transaction in TRANSACTION_RULES.values():
    for _check in _transaction["checks"]:
        if _check not in _CHECK_IMPLEMENTATIONS:
            raise RuntimeError(f"No implementation for declared check {_check!r}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _has_document(documents: dict[str, Any], key: str) -> bool:
    entry = documents.get(key)
    if not entry:
        return False
    if isinstance(entry, dict) and entry.get("missing") is True:
        return False
    return True


def _field(documents: dict[str, Any], doc_key: str, field_name: str) -> Any:
    entry = documents.get(doc_key) or {}
    if not isinstance(entry, dict):
        return None
    fields = entry.get("fields")
    if isinstance(fields, dict) and fields.get(field_name) is not None:
        return fields[field_name]
    return entry.get(field_name)


def _normalise_id(value: Any) -> str:
    """Strip spaces/punctuation so '12 345 678' == '12345678'."""
    return re.sub(r"\D", "", str(value)) if value is not None else ""


def _all_ids(documents: dict[str, Any], doc_key: str) -> list[str]:
    """Every ID number a document mentions, normalised and de-duplicated."""
    found: list[str] = []
    primary = _normalise_id(_field(documents, doc_key, "id_number"))
    if primary:
        found.append(primary)

    others = _field(documents, doc_key, "other_id_numbers") or []
    if isinstance(others, (list, tuple)):
        found.extend(filter(None, (_normalise_id(item) for item in others)))

    return list(dict.fromkeys(found))


def _parse_date(value: Any) -> date | None:
    """Accept date/datetime objects and the usual written formats."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not value:
        return None

    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _name_present(person: str, haystack: str) -> bool:
    """Loose name match: every significant token must appear.

    Tolerates reordering ("Ben Salah Amine") and extra particles, which OCR and
    administrative documents both produce freely.
    """
    normalise = lambda text: re.sub(r"[^\w\s]", " ", str(text).casefold())  # noqa: E731
    hay = set(normalise(haystack).split())
    tokens = [t for t in normalise(person).split() if len(t) > 2]
    return bool(tokens) and all(token in hay for token in tokens)
