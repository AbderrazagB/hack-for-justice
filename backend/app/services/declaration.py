"""The RNE declaration (form RNE-F-005) as structured data.

Sahilli never saw this before: it checked the *attachments* and ignored the
*declaration*. Yet the declaration is where rejections come from -- the form
itself warns that "كل بيان ناقص موجب لرفض الطلب" (any incomplete entry causes
the request to be rejected) and that a declaration contradicting reality is
void under article 55 of Law 52-2018.

So the point of capturing it is not to produce a PDF. It is to compare what
the applicant *declares* against what their documents actually *say*, and
catch the contradiction before the registry does.

One form covers every procedure: RNE-F-005's checkbox grid includes updating
managers, depositing financial statements, updating partners, appointing an
auditor and around twenty more. The field list below is therefore shared by
all transactions; only `modification_types` differs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Modification types on the form, keyed by the transaction that uses them.
# Values are the Arabic labels as they appear in the checkbox grid, since the
# form is filled in Arabic.
MODIFICATION_TYPES: dict[str, dict[str, str]] = {
    "update_managers": {
        "fr": "Ajout ou mise à jour des dirigeants",
        "ar": "إضافة أو تحيين المسيّرين",
    },
    "deposit_financial_statements": {
        "fr": "Dépôt des états financiers",
        "ar": "إيداع القوائم المالية",
    },
    "update_partners": {
        "fr": "Mise à jour des associés ou actionnaires",
        "ar": "تحيين الشركاء أو المساهمين",
    },
    "update_statutes": {
        "fr": "Mise à jour du statut juridique",
        "ar": "تحيين القانون الأساسي",
    },
}

# Which type each transaction ticks on the form.
TRANSACTION_MODIFICATION_TYPE: dict[str, str] = {
    "RNE_MODIFICATION_ENTREPRISE": "update_managers",
    "RNE_FINANCIAL_STATEMENTS": "deposit_financial_statements",
}


@dataclass(frozen=True)
class DeclarationField:
    name: str
    label_fr: str
    label_ar: str
    # "text" | "email" | "tel" | "id"
    type: str = "text"
    required: bool = True
    help_fr: str | None = None


# Exactly the fields printed on RNE-F-005, in the order the form prints them.
DECLARATION_FIELDS: list[DeclarationField] = [
    DeclarationField(
        "legal_representative",
        "Représentant légal",
        "الممثل القانوني",
        help_fr="Nom du représentant légal tel qu'il figurera au registre.",
    ),
    DeclarationField(
        "email",
        "Adresse e-mail",
        "البريد الإلكتروني",
        type="email",
        help_fr="Obligatoire : le RNE s'en sert pour vous notifier l'état du dossier.",
    ),
    DeclarationField(
        "phone",
        "Téléphone mobile",
        "الهاتف الجوال",
        type="tel",
        help_fr="Obligatoire, au même titre que l'e-mail.",
    ),
    DeclarationField(
        "declarant_name", "Nom et prénom du déclarant", "إسم و لقب المصرّح"
    ),
    DeclarationField(
        "declarant_id",
        "Numéro d'identité du déclarant",
        "رقم بطاقة هوية المصرّح",
        type="id",
    ),
    DeclarationField(
        "entity_id", "Numéro d'identité", "رقم الهوية", type="id", required=False
    ),
    DeclarationField(
        "unique_identifier",
        "Identifiant unique",
        "المعرّف الوحيد",
        help_fr="L'identifiant de l'entreprise au registre.",
    ),
    DeclarationField(
        "reservation_certificate",
        "N° certificat de réservation",
        "رقم شهادة الحجز",
        required=False,
        help_fr="Le cas échéant.",
    ),
    DeclarationField(
        "rib",
        "RIB",
        "المعرّف البنكي",
        required=False,
        help_fr="Uniquement en cas de changement de compte bancaire.",
    ),
]

FIELDS_BY_NAME = {f.name: f for f in DECLARATION_FIELDS}


@dataclass
class DeclarationIssue:
    """One problem with the declaration itself, or with how it matches."""

    code: str
    message_fr: str
    message_ar: str
    # Named field_name, not field: inside a dataclass body an attribute called
    # `field` shadows dataclasses.field for every line after it.
    field_name: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)


def _digits(value: Any) -> str:
    return re.sub(r"\D", "", str(value)) if value not in (None, "") else ""


def _normalise_name(value: Any) -> set[str]:
    """Significant tokens of a name, case- and punctuation-insensitive."""
    text = re.sub(r"[^\w\s]", " ", str(value or "").casefold())
    return {token for token in text.split() if len(token) > 2}


def missing_required(declaration: dict[str, Any]) -> list[DeclarationField]:
    """Fields the form requires that the applicant left blank.

    The form is explicit that an incomplete entry is grounds for rejection, so
    this is a real rule and not a nicety.
    """
    return [
        spec
        for spec in DECLARATION_FIELDS
        if spec.required and not str(declaration.get(spec.name) or "").strip()
    ]


def cross_check(
    declaration: dict[str, Any], documents: dict[str, Any]
) -> list[DeclarationIssue]:
    """Compare the declared values against what OCR read from the documents.

    Only reports a disagreement when both sides are present and readable. An
    unreadable document is not evidence that the applicant declared wrongly.
    """
    issues: list[DeclarationIssue] = []

    def field_of(doc: str, name: str) -> Any:
        entry = documents.get(doc) or {}
        fields = entry.get("fields") if isinstance(entry, dict) else None
        return (fields or {}).get(name) if isinstance(fields, dict) else None

    # --- declarant's ID against the national ID card -------------------------
    declared_id = _digits(declaration.get("declarant_id"))
    card_id = _digits(field_of("id_new_representative", "id_number"))
    if declared_id and card_id and declared_id != card_id:
        issues.append(
            DeclarationIssue(
                "declared_id_differs_from_id_card",
                f"Le numéro d'identité déclaré ({declared_id}) ne correspond pas "
                f"à celui lu sur la carte d'identité ({card_id}).",
                f"رقم الهوية المصرّح به ({declared_id}) لا يطابق الرقم المقروء "
                f"على بطاقة التعريف ({card_id}).",
                field_name="declarant_id",
                evidence={"declared": declared_id, "document": card_id},
            )
        )

    # --- unique identifier against the extract and the tax card --------------
    declared_unique = _digits(declaration.get("unique_identifier"))
    for doc, label in (
        ("rne_extract", "l'Extrait RNE"),
        ("company_statutes", "les statuts"),
    ):
        document_unique = _digits(field_of(doc, "company_id"))
        if declared_unique and document_unique and declared_unique != document_unique:
            issues.append(
                DeclarationIssue(
                    "declared_identifier_differs_from_documents",
                    f"L'identifiant unique déclaré ({declared_unique}) ne "
                    f"correspond pas à celui figurant sur {label} "
                    f"({document_unique}).",
                    f"المعرّف الوحيد المصرّح به ({declared_unique}) لا يطابق "
                    f"المعرّف الوارد بالوثائق ({document_unique}).",
                    field_name="unique_identifier",
                    evidence={"declared": declared_unique, "document": document_unique},
                )
            )
            break

    # --- legal representative's name against the ID card and the minutes -----
    declared_rep = _normalise_name(declaration.get("legal_representative"))
    if declared_rep:
        candidates = [
            _normalise_name(field_of(doc, "person_name"))
            for doc in ("id_new_representative", "general_assembly_pv")
        ]
        readable = [c for c in candidates if c]
        if readable and not any(declared_rep & names for names in readable):
            shown = " / ".join(sorted(" ".join(sorted(c)) for c in readable))
            issues.append(
                DeclarationIssue(
                    "declared_representative_not_in_documents",
                    "Le représentant légal déclaré ne correspond à aucun nom lu "
                    f"sur les pièces fournies ({shown}).",
                    "الممثل القانوني المصرّح به لا يطابق أي اسم مقروء على "
                    "الوثائق المقدمة.",
                    field_name="legal_representative",
                    evidence={"declared": str(declaration.get("legal_representative"))},
                )
            )

    return issues
