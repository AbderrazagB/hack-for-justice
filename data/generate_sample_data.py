"""Synthetic Tunisian demo data for Sahilli.

Generates fake MSME filings for the Modification Entreprise workflow and
renders each one as a simple image, so the OCR pipeline has something real to
process end to end on stage rather than being fed pre-parsed JSON.

Includes deliberately broken cases -- mismatched CIN, missing signature date,
filed past the one-month window, stale Extrait -- so the flagging logic visibly
catches something during the demo.

Everything here is fabricated. Names, CIN numbers and company identifiers are
Faker output shaped to look Tunisian; they are not real people or companies,
and the rendered images are obvious mock-ups, not forgeries of official
documents.

    uv run python data/generate_sample_data.py --out data/demo
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
from faker import Faker
from PIL import Image, ImageDraw

DOCUMENT_TYPES = [
    "id_new_representative",
    "company_statutes",
    "rne_extract",
    "tax_registration_card",
    "general_assembly_pv",
]

FINANCIAL_DOCUMENT_TYPES = [
    "financial_statements_signed",
    "general_assembly_pv_approval",
    "auditor_report",
    "updated_shareholder_list",
]

LEGAL_FORMS = ["SARL", "SUARL", "SA"]
GOVERNORATES = [
    "Tunis", "Ariana", "Ben Arous", "Sfax", "Sousse",
    "Nabeul", "Bizerte", "Gabès", "Monastir", "Kairouan",
]
ACTIVITIES = [
    "Commerce de détail", "Services informatiques", "Industrie agroalimentaire",
    "Transport et logistique", "Conseil et ingénierie", "Textile et habillement",
]

# The reference "today" for generated data. Fixed so a regenerated dataset
# produces the same verdicts as the one the demo was rehearsed against.
REFERENCE_DATE = date(2026, 9, 1)


@dataclass
class Case:
    """One generated filing, plus what it is supposed to demonstrate."""

    case_id: str
    label: str
    intent: str                      # "clean" or the defect being demonstrated
    expected_status: str             # what the rules engine should conclude
    expected_flags: list[str] = field(default_factory=list)
    company_name: str = ""
    company_id: str = ""
    tax_id: str = ""
    legal_form: str = ""
    governorate: str = ""
    activity: str = ""
    outgoing_representative: str = ""
    new_representative: str = ""
    cin: str = ""
    cin_in_pv: str = ""
    decision_date: str = ""
    signature_date: str | None = ""
    extract_issue_date: str = ""
    statutes_representative: str = ""
    submitted_at: str = ""
    documents: dict[str, str] = field(default_factory=dict)

    # Financial-statements workflow. Empty on modification cases.
    transaction_type: str = "RNE_MODIFICATION_ENTREPRISE"
    company_type: str = ""
    fiscal_year_end: str = ""
    auditor_required: bool = False
    auditor_name: str = ""
    shareholders: list[dict[str, str | None]] = field(default_factory=list)
    statements_signed: bool = True
    statements_stamped: bool = True
    pv_registration_reference: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _cin(fake: Faker) -> str:
    """Tunisian CIN shape: 8 digits. Fabricated, not a real identity."""
    return fake.numerify("########")


def _company_id(fake: Faker) -> str:
    """RNE-style unique identifier, fabricated."""
    return fake.numerify("#######") + fake.random_element("ABCDEFGHJKLMNPQRSTVWXYZ")


def _tax_id(company_id: str) -> str:
    return f"{company_id}/A/M/000"


def _company_name(fake: Faker) -> str:
    return f"{fake.random_element(LEGAL_FORMS)} {fake.last_name().upper()} {fake.random_element(['TRADING', 'SERVICES', 'INDUSTRIE', 'DISTRIBUTION', 'CONSEIL'])}"


def _person(fake: Faker) -> str:
    return f"{fake.first_name()} {fake.last_name()}"


def build_cases(count: int = 8, seed: int = 2026) -> list[Case]:
    """Build the demo set: broken cases first, then clean ones to fill out."""
    fake = Faker("fr_FR")
    Faker.seed(seed)
    random.seed(seed)

    cases: list[Case] = []

    def base(case_id: str, label: str, intent: str, expected_status: str) -> Case:
        company_id = _company_id(fake)
        new_rep = _person(fake)
        cin = _cin(fake)
        decision = REFERENCE_DATE - timedelta(days=random.randint(3, 20))
        return Case(
            case_id=case_id,
            label=label,
            intent=intent,
            expected_status=expected_status,
            company_name=_company_name(fake),
            company_id=company_id,
            tax_id=_tax_id(company_id),
            legal_form=random.choice(LEGAL_FORMS),
            governorate=random.choice(GOVERNORATES),
            activity=random.choice(ACTIVITIES),
            outgoing_representative=_person(fake),
            new_representative=new_rep,
            cin=cin,
            cin_in_pv=cin,
            decision_date=decision.isoformat(),
            signature_date=decision.isoformat(),
            extract_issue_date=(REFERENCE_DATE - timedelta(days=random.randint(5, 60))).isoformat(),
            statutes_representative=new_rep,
            submitted_at=REFERENCE_DATE.isoformat(),
        )

    # --- Broken case 1: the CIN on the PV is not the CIN on the ID card ------
    mismatch = base(
        "DEMO-001",
        "CIN mismatch between national ID and PV",
        "mismatched_id_numbers",
        "NEEDS_REVIEW",
    )
    mismatch.cin_in_pv = _cin(fake)
    mismatch.expected_flags = ["id_number_matches_across_documents"]
    cases.append(mismatch)

    # --- Broken case 2: PV carries no signature date ------------------------
    unsigned = base(
        "DEMO-002",
        "General assembly PV missing its signature date",
        "missing_signature_date",
        "NEEDS_REVIEW",
    )
    unsigned.signature_date = None
    unsigned.expected_flags = ["pv_is_signed"]
    cases.append(unsigned)

    # --- Broken case 3: filed well past the one-month statutory window ------
    late = base(
        "DEMO-003",
        "Filed 74 days after the decision, past the one-month window",
        "filed_late",
        "NEEDS_REVIEW",
    )
    late_decision = REFERENCE_DATE - timedelta(days=74)
    late.decision_date = late_decision.isoformat()
    late.signature_date = late_decision.isoformat()
    late.expected_flags = ["filed_within_legal_deadline_of_decision_date"]
    cases.append(late)

    # --- Broken case 4: stale Extrait RNE + statutes naming the wrong person -
    stale = base(
        "DEMO-004",
        "Extrait RNE 8 months old and statutes naming the outgoing manager",
        "stale_extract_and_wrong_statutes",
        "NEEDS_REVIEW",
    )
    stale.extract_issue_date = (REFERENCE_DATE - timedelta(days=245)).isoformat()
    stale.statutes_representative = stale.outgoing_representative
    stale.expected_flags = [
        "rne_extract_not_older_than_90_days",
        "statutes_reflect_new_representative_name",
    ]
    cases.append(stale)

    # --- Clean cases --------------------------------------------------------
    for index in range(len(cases) + 1, count + 1):
        clean = base(
            f"DEMO-{index:03d}",
            "Complete and consistent filing",
            "clean",
            "COMPLETE",
        )
        cases.append(clean)

    return cases


def build_financial_cases(count: int = 6, seed: int = 2026) -> list[Case]:
    """Cases for the annual financial statements filing.

    Mirrors build_cases: broken examples first, then clean ones. Seeded, so a
    rehearsed demo stays the rehearsed demo.
    """
    fake = Faker("fr_FR")
    Faker.seed(seed + 500)
    random.seed(seed + 500)

    def base(case_id: str, label: str, intent: str, expected_status: str) -> Case:
        company_id = _company_id(fake)
        holders = [
            {"name": _person(fake), "id_number": _cin(fake)}
            for _ in range(random.randint(2, 4))
        ]
        return Case(
            case_id=case_id,
            label=label,
            intent=intent,
            expected_status=expected_status,
            transaction_type="RNE_FINANCIAL_STATEMENTS",
            company_name=_company_name(fake),
            company_id=company_id,
            tax_id=_tax_id(company_id),
            legal_form="SARL",
            governorate=random.choice(GOVERNORATES),
            activity=random.choice(ACTIVITIES),
            new_representative=_person(fake),
            auditor_name=_person(fake),
            company_type="SARL",
            fiscal_year_end="2025-12-31",
            shareholders=holders,
            pv_registration_reference=f"RF-2026-{fake.numerify('####')}",
            # Comfortably inside the seven-month window that closed 31/07/2026.
            submitted_at="2026-07-15",
        )

    cases: list[Case] = []

    # --- Broken 1: an SA with no commissaire aux comptes report --------------
    no_auditor = base(
        "FIN-001",
        "SA filing with no statutory auditor report",
        "missing_auditor_report",
        "INCOMPLETE",
    )
    no_auditor.company_type = "SA"
    no_auditor.legal_form = "SA"
    no_auditor.auditor_required = True
    no_auditor.auditor_name = ""  # renderer skips the document entirely
    no_auditor.expected_flags = ["auditor_report_present_if_required_by_company_type"]
    cases.append(no_auditor)

    # --- Broken 2: filed well past the seven-month deadline -----------------
    late = base(
        "FIN-002",
        "Filed 2026-10-15, past the 31/07/2026 deadline",
        "filed_late",
        "NEEDS_REVIEW",
    )
    late.submitted_at = "2026-10-15"
    late.expected_flags = ["filed_within_7_months_of_fiscal_year_close"]
    cases.append(late)

    # --- Broken 3: statements carry no company stamp ------------------------
    unstamped = base(
        "FIN-003",
        "Financial statements signed but not stamped",
        "statements_not_stamped",
        "NEEDS_REVIEW",
    )
    unstamped.statements_stamped = False
    unstamped.expected_flags = ["financial_statements_signed_and_stamped"]
    cases.append(unstamped)

    # --- Broken 4: a partner listed with no identity reference --------------
    missing_id = base(
        "FIN-004",
        "Shareholder list with a partner missing their CIN",
        "shareholder_without_id",
        "NEEDS_REVIEW",
    )
    missing_id.shareholders = list(missing_id.shareholders)
    missing_id.shareholders[-1] = {
        "name": missing_id.shareholders[-1]["name"],
        "id_number": None,
    }
    missing_id.expected_flags = ["shareholder_list_ids_present_for_each_entry"]
    cases.append(missing_id)

    # --- Clean cases --------------------------------------------------------
    for index in range(len(cases) + 1, count + 1):
        clean = base(
            f"FIN-{index:03d}",
            "Complete and consistent annual filing",
            "clean",
            "COMPLETE",
        )
        cases.append(clean)

    return cases


# ---------------------------------------------------------------- rendering

# Rendering these with PIL's built-in bitmap font produced text small and coarse
# enough that the vision model misread single digits -- a clean case once came
# back flagged because an 8-digit CIN differed by one character between two
# documents. Real TrueType faces at a legible size fix that at the source;
# identifiers additionally use a mono face, where 6/8/0 are unambiguous.
_FONT_CANDIDATES = {
    "body": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ],
    "bold": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ],
    "mono": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
    ],
}


def _font(kind: str, size: int):
    """Load a real face, falling back to PIL's bitmap font if none is installed."""
    from PIL import ImageFont

    for candidate in _FONT_CANDIDATES[kind]:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


# A line reading "Label: VALUE" where VALUE is an identifier gets the mono face
# for the value, so digits stay unambiguous to OCR.
_IDENTIFIER_PREFIXES = (
    "N:",
    "CIN:",
    "Identifiant unique:",
    "Identifiant fiscal:",
    "Date de la decision:",
    "Date de delivrance:",
)


def _render(lines: list[tuple[str, bool]], path: Path, width: int = 1400) -> None:
    """Render a mock document. `lines` is (text, is_heading)."""
    body = _font("body", 30)
    bold = _font("bold", 34)
    mono = _font("mono", 34)

    line_height = 62
    height = 120 + len(lines) * line_height
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    draw.rectangle([24, 24, width - 24, height - 24], outline="black", width=3)

    y = 62
    for text, heading in lines:
        if heading:
            draw.text((60, y), text, fill="black", font=bold)
            draw.line([60, y + 44, width - 70, y + 44], fill="black", width=2)
        elif any(text.startswith(prefix) for prefix in _IDENTIFIER_PREFIXES):
            label, _, value = text.partition(":")
            draw.text((60, y), f"{label}:", fill="black", font=body)
            offset = draw.textlength(f"{label}: ", font=body)
            draw.text((60 + offset, y - 3), value.strip(), fill="black", font=mono)
        else:
            draw.text((60, y), text, fill="black", font=body)
        y += line_height

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def render_financial_documents(case: Case, out_dir: Path) -> dict[str, str]:
    """Render the four annual-filing documents for one case."""
    case_dir = out_dir / case.case_id
    written: dict[str, str] = {}

    def emit(doc_type: str, lines: list[tuple[str, bool]]) -> None:
        path = case_dir / f"{doc_type}.png"
        _render(lines + [("-- DOCUMENT FICTIF / وثيقة وهمية --", False)], path)
        written[doc_type] = str(path)

    statements = [
        ("ETATS FINANCIERS ANNUELS", True),
        (f"Societe: {case.company_name}", False),
        (f"Identifiant unique: {case.company_id}", False),
        (f"Exercice clos le: {case.fiscal_year_end}", False),
        ("Bilan - Etat de resultat - Notes aux etats financiers", False),
    ]
    statements.append(
        ("Signature du gerant        Cachet de la societe", False)
        if case.statements_signed and case.statements_stamped
        else ("Signature du gerant        (sans cachet)", False)
    )
    emit("financial_statements_signed", statements)

    emit("general_assembly_pv_approval", [
        ("PROCES-VERBAL DE L'ASSEMBLEE GENERALE ORDINAIRE", True),
        (f"Societe: {case.company_name}", False),
        (f"Exercice clos le: {case.fiscal_year_end}", False),
        ("Objet: approbation des comptes annuels", False),
        (f"Enregistrement recette des finances: {case.pv_registration_reference}", False),
        ("Signature du president de seance", False),
    ])

    if case.auditor_name:
        emit("auditor_report", [
            ("RAPPORT DU COMMISSAIRE AUX COMPTES", True),
            (f"Societe: {case.company_name}", False),
            (f"Exercice clos le: {case.fiscal_year_end}", False),
            (f"Commissaire aux comptes: {case.auditor_name}", False),
            ("Opinion: les etats financiers sont reguliers et sinceres.", False),
            ("Signature du commissaire aux comptes", False),
        ])

    holder_lines: list[tuple[str, bool]] = [
        ("LISTE ACTUALISEE DES ASSOCIES", True),
        (f"Societe: {case.company_name}", False),
    ]
    for holder in case.shareholders:
        cin = holder["id_number"] or "________"
        holder_lines.append((f"{holder['name']}    CIN: {cin}", False))
    emit("updated_shareholder_list", holder_lines)

    return written


def render_documents(case: Case, out_dir: Path) -> dict[str, str]:
    """Render all five documents for one case. Returns doc_type -> path."""
    case_dir = out_dir / case.case_id
    written: dict[str, str] = {}

    def emit(doc_type: str, lines: list[tuple[str, bool]]) -> None:
        path = case_dir / f"{doc_type}.png"
        _render(lines + [("-- DOCUMENT FICTIF / وثيقة وهمية --", False)], path)
        written[doc_type] = str(path)

    emit("id_new_representative", [
        ("REPUBLIQUE TUNISIENNE", True),
        ("CARTE D'IDENTITE NATIONALE", True),
        (f"N: {case.cin}", False),
        (f"Nom et prenom: {case.new_representative}", False),
        (f"Lieu: {case.governorate}", False),
    ])

    emit("company_statutes", [
        (f"STATUTS DE LA SOCIETE {case.legal_form}", True),
        (f"Denomination: {case.company_name}", False),
        (f"Siege social: {case.governorate}", False),
        (f"Activite: {case.activity}", False),
        (f"Gerant: {case.statutes_representative}", False),
        (f"Identifiant unique: {case.company_id}", False),
    ])

    emit("rne_extract", [
        ("REGISTRE NATIONAL DES ENTREPRISES", True),
        ("EXTRAIT RNE", True),
        (f"Denomination: {case.company_name}", False),
        (f"Identifiant unique: {case.company_id}", False),
        (f"Representant legal: {case.outgoing_representative}", False),
        (f"Date de delivrance: {case.extract_issue_date}", False),
    ])

    emit("tax_registration_card", [
        ("CARTE D'IDENTIFICATION FISCALE", True),
        ("DECLARATION D'EXISTENCE", True),
        (f"Denomination: {case.company_name}", False),
        (f"Identifiant fiscal: {case.tax_id}", False),
        (f"Activite: {case.activity}", False),
    ])

    pv_lines = [
        ("PROCES-VERBAL DE L'ASSEMBLEE GENERALE", True),
        (f"Societe: {case.company_name}", False),
        (f"Date de la decision: {case.decision_date}", False),
        ("Objet: changement de representant legal", False),
        (f"Representant sortant: {case.outgoing_representative}", False),
        (f"Nouveau representant: {case.new_representative}", False),
        (f"CIN: {case.cin_in_pv}", False),
    ]
    pv_lines.append(
        (f"Signature du gerant    Date: {case.signature_date}", False)
        if case.signature_date
        else ("Signature du gerant    Date: ________________", False)
    )
    emit("general_assembly_pv", pv_lines)

    return written


# -------------------------------------------------------------------- output

def generate_sample_data(count: int = 8, seed: int = 2026) -> pd.DataFrame:
    """Return the generated cases as a DataFrame (no files written)."""
    return pd.DataFrame([case.to_dict() for case in build_cases(count, seed)])


def write_dataset(
    out_dir: Path, count: int = 8, seed: int = 2026, financial_count: int = 6
) -> list[Case]:
    """Generate cases for both workflows, render them, and write a manifest."""
    out_dir.mkdir(parents=True, exist_ok=True)

    cases = build_cases(count, seed)
    for case in cases:
        case.documents = render_documents(case, out_dir)

    financial = build_financial_cases(financial_count, seed)
    for case in financial:
        case.documents = render_financial_documents(case, out_dir)
    cases.extend(financial)

    manifest = {
        "generated_for": "Sahilli — RNE Modification Entreprise + États Financiers",
        "reference_date": REFERENCE_DATE.isoformat(),
        "warning": "All data is synthetic. Not real people, companies, or documents.",
        "cases": [case.to_dict() for case in cases],
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return cases


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("data/demo"))
    parser.add_argument("--count", type=int, default=8)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--financial-count", type=int, default=6)
    args = parser.parse_args()

    cases = write_dataset(args.out, args.count, args.seed, args.financial_count)

    print(f"Wrote {len(cases)} cases to {args.out}/")
    for case in cases:
        marker = "OK  " if case.intent == "clean" else "BAD "
        print(f"  {marker}{case.case_id}  {case.expected_status:<12} {case.label}")
    print(f"\nManifest: {args.out / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
