"""Synthetic Tunisian demo data for Sahilli.

Generates fake MSME filings for the Modification Entreprise workflow and
renders each one as a simple image, so the OCR pipeline has something real to
process end to end on stage rather than being fed pre-parsed JSON.

Includes deliberately broken cases -- mismatched CIN, missing signature date,
filed past the 30-day window, stale Extrait -- so the flagging logic visibly
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

    # --- Broken case 3: filed well past the 30-day statutory window ---------
    late = base(
        "DEMO-003",
        "Filed 74 days after the decision, past the 30-day window",
        "filed_late",
        "NEEDS_REVIEW",
    )
    late_decision = REFERENCE_DATE - timedelta(days=74)
    late.decision_date = late_decision.isoformat()
    late.signature_date = late_decision.isoformat()
    late.expected_flags = ["filed_within_30_days_of_decision_date"]
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


# ---------------------------------------------------------------- rendering

def _render(lines: list[tuple[str, bool]], path: Path, width: int = 1000) -> None:
    """Render a mock document. `lines` is (text, is_heading)."""
    height = 90 + len(lines) * 46
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    draw.rectangle([20, 20, width - 20, height - 20], outline="black", width=2)
    y = 50
    for text, heading in lines:
        draw.text((50, y), text, fill="black")
        if heading:
            draw.line([50, y + 22, width - 60, y + 22], fill="black", width=1)
        y += 46

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


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


def write_dataset(out_dir: Path, count: int = 8, seed: int = 2026) -> list[Case]:
    """Generate cases, render their documents, and write a manifest."""
    out_dir.mkdir(parents=True, exist_ok=True)
    cases = build_cases(count, seed)

    for case in cases:
        case.documents = render_documents(case, out_dir)

    manifest = {
        "generated_for": "Sahilli — RNE Modification Entreprise (RNE-M-005)",
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
    args = parser.parse_args()

    cases = write_dataset(args.out, args.count, args.seed)

    print(f"Wrote {len(cases)} cases to {args.out}/")
    for case in cases:
        marker = "OK  " if case.intent == "clean" else "BAD "
        print(f"  {marker}{case.case_id}  {case.expected_status:<12} {case.label}")
    print(f"\nManifest: {args.out / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
