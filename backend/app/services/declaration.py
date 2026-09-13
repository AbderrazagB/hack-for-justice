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
    # Why the question is asked, in the applicant's own words.
    #
    # Deliberately static text rather than model output: an explanation of a
    # rule has to be as reproducible as the rule itself, or it explains nothing.
    # Each one states only what is verifiable in this file -- whether RNE-F-005
    # marks the entry obligatory, and which document cross_check() compares the
    # answer against. Where nothing is compared, it says so, so that a green
    # result is never read as more assurance than it is.
    why_fr: str | None = None
    why_ar: str | None = None


# Exactly the fields printed on RNE-F-005, in the order the form prints them.
DECLARATION_FIELDS: list[DeclarationField] = [
    DeclarationField(
        "legal_representative",
        "Représentant légal",
        "الممثل القانوني",
        help_fr="Nom du représentant légal tel qu'il figurera au registre.",
        why_fr=(
            "Nous comparons ce nom à ceux lus sur la carte d'identité et sur le "
            "procès-verbal d'assemblée. S'il ne correspond à aucun des deux, "
            "vous le saurez ici plutôt qu'après le dépôt."
        ),
        why_ar=(
            "نقارن هذا الاسم بما هو مقروء على بطاقة التعريف وعلى محضر الجلسة. "
            "إن لم يطابق أيّاً منهما، ستعلم ذلك الآن لا بعد الإيداع."
        ),
    ),
    DeclarationField(
        "email",
        "Adresse e-mail",
        "البريد الإلكتروني",
        type="email",
        help_fr="Obligatoire : le RNE s'en sert pour vous notifier l'état du dossier.",
        why_fr=(
            "Obligatoire sur le formulaire RNE-F-005. C'est par cette adresse "
            "que le registre vous notifie sa décision. Elle n'est recoupée avec "
            "aucune pièce : nous vérifions seulement qu'elle est renseignée."
        ),
        why_ar=(
            "وجوبي في مطبوعة RNE-F-005، وعبره يبلّغك السجل بقراره. لا تتم "
            "مقارنته بأي وثيقة، بل نتثبّت فقط من تعميره."
        ),
    ),
    DeclarationField(
        "phone",
        "Téléphone mobile",
        "الهاتف الجوال",
        type="tel",
        help_fr="Obligatoire, au même titre que l'e-mail.",
        why_fr=(
            "Obligatoire sur le formulaire, au même titre que l'e-mail. Second "
            "canal de notification. Il n'est recoupé avec aucune pièce."
        ),
        why_ar=(
            "وجوبي في المطبوعة شأنه شأن البريد الإلكتروني، وهو قناة إعلام ثانية. "
            "لا تتم مقارنته بأي وثيقة."
        ),
    ),
    DeclarationField(
        "declarant_name",
        "Nom et prénom du déclarant",
        "إسم و لقب المصرّح",
        why_fr=(
            "La personne qui signe la déclaration, et qui n'est pas forcément "
            "le représentant légal : un mandataire ou un comptable peut déposer. "
            "Le formulaire la demande séparément pour cette raison."
        ),
        why_ar=(
            "الشخص الذي يمضي التصريح، وليس بالضرورة الممثل القانوني: قد يتولى "
            "الإيداع وكيل أو محاسب. لذلك تطلبه المطبوعة على حدة."
        ),
    ),
    DeclarationField(
        "declarant_id",
        "Numéro d'identité du déclarant",
        "رقم بطاقة هوية المصرّح",
        type="id",
        why_fr=(
            "Nous le comparons au numéro lu sur la carte d'identité jointe. Un "
            "chiffre inversé ici suffit à faire rejeter le dossier, et c'est "
            "exactement le genre d'écart que la vérification rattrape."
        ),
        why_ar=(
            "نقارنه بالرقم المقروء على بطاقة التعريف المرفقة. يكفي قلب رقم واحد "
            "لرفض الملف، وهذا بالضبط ما يلتقطه التثبّت."
        ),
    ),
    DeclarationField(
        "entity_id",
        "Numéro d'identité",
        "رقم الهوية",
        type="id",
        required=False,
        why_fr=(
            "Facultatif : la case ne concerne que les déclarants qui disposent "
            "d'un numéro d'identité distinct de celui porté plus haut. "
            "Laissez-la vide si ce n'est pas votre cas."
        ),
        why_ar=(
            "اختياري: لا تعني هذه الخانة إلا من له رقم هوية مغاير لما ذُكر "
            "أعلاه. اتركها فارغة إن لم تكن حالتك."
        ),
    ),
    DeclarationField(
        "unique_identifier",
        "Identifiant unique",
        "المعرّف الوحيد",
        help_fr="L'identifiant de l'entreprise au registre.",
        why_fr=(
            "Nous le comparons à l'identifiant lu sur l'Extrait RNE, puis sur "
            "les statuts. C'est la clé sous laquelle le registre retrouve votre "
            "entreprise : s'il est erroné, la demande ne s'attache à rien."
        ),
        why_ar=(
            "نقارنه بالمعرّف المقروء على مضمون السجل ثم على العقد التأسيسي. هو "
            "المفتاح الذي يجد به السجل مؤسستك: إن كان خاطئاً لم يتعلق المطلب بشيء."
        ),
    ),
    DeclarationField(
        "reservation_certificate",
        "N° certificat de réservation",
        "رقم شهادة الحجز",
        required=False,
        help_fr="Le cas échéant.",
        why_fr=(
            "Facultatif : à ne remplir que si une dénomination a été réservée "
            "auprès du registre et que la présente démarche s'y rapporte."
        ),
        why_ar=(
            "اختياري: لا يُعمّر إلا إذا وقع حجز تسمية لدى السجل وكان هذا المطلب "
            "متصلاً بها."
        ),
    ),
    DeclarationField(
        "rib",
        "RIB",
        "المعرّف البنكي",
        required=False,
        help_fr="Uniquement en cas de changement de compte bancaire.",
        why_fr=(
            "Facultatif : à ne remplir qu'en cas de changement de compte "
            "bancaire. Il n'est recoupé avec aucune pièce."
        ),
        why_ar=(
            "اختياري: لا يُعمّر إلا عند تغيير الحساب البنكي. لا تتم مقارنته بأي وثيقة."
        ),
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
