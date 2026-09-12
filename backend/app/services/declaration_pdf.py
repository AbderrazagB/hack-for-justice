"""Generate the applicant's preparation sheet for RNE-F-005.

NOT an official filing. Since 1 July 2026 the RNE accepts declarations only
through its own portal, signed with e-Houwiya or a recognised electronic
signature -- a handwritten signature on a printed PDF is the paper process the
registry has just abolished. So this sheet exists to be *read from*, not
submitted: one page holding every answer the applicant will type into the
portal, plus the documents they have prepared. The header says so explicitly,
in both languages, so nobody mistakes it for the form itself.

Arabic needs two steps that Latin does not: reshaping joins the letters into
their contextual forms, and the bidi algorithm puts the run in visual order.
Without both, Arabic renders as disconnected letters in reverse.
"""

from __future__ import annotations

import io
from datetime import date
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdfcanvas

from app.services.declaration import DECLARATION_FIELDS

NAVY = colors.HexColor("#0E2747")
TEAL = colors.HexColor("#0B6E68")
INK = colors.HexColor("#16273B")
MUTED = colors.HexColor("#5A6E85")
LINE = colors.HexColor("#DEE5EC")

# DejaVu carries both Latin and Arabic; the Liberation fallback keeps Latin
# working on a host without DejaVu, at the cost of Arabic glyphs.
_FONT_CANDIDATES = {
    "body": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ],
    "bold": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ],
}

_registered: dict[str, str] = {}


def _font(kind: str) -> str:
    """Register a real TTF once and return its name, or fall back to Helvetica."""
    if kind in _registered:
        return _registered[kind]

    for candidate in _FONT_CANDIDATES[kind]:
        if Path(candidate).exists():
            name = f"sahilli-{kind}"
            pdfmetrics.registerFont(TTFont(name, candidate))
            _registered[kind] = name
            return name

    _registered[kind] = "Helvetica-Bold" if kind == "bold" else "Helvetica"
    return _registered[kind]


def shape_arabic(text: str) -> str:
    """Join and reorder an Arabic run for PDF rendering.

    Returns the text unchanged when it holds no Arabic, and on any failure --
    a missing shaper should degrade the glyphs, not fail the download.
    """
    if not any("؀" <= ch <= "ۿ" for ch in text):
        return text
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display

        return get_display(arabic_reshaper.reshape(text))
    except Exception:  # noqa: BLE001
        return text


def build_preparation_sheet(
    submission: dict[str, Any], generated_on: date | None = None
) -> bytes:
    """Render the sheet as PDF bytes."""
    generated_on = generated_on or date.today()
    declaration = (submission.get("context") or {}).get("declaration") or {}
    completeness = submission.get("completeness") or {}

    buffer = io.BytesIO()
    pdf = pdfcanvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    body, bold = _font("body"), _font("bold")

    margin = 18 * mm
    y = height - margin

    # ---- header -----------------------------------------------------------
    pdf.setFillColor(NAVY)
    pdf.rect(0, height - 30 * mm, width, 30 * mm, fill=1, stroke=0)

    pdf.setFillColor(colors.white)
    pdf.setFont(bold, 16)
    pdf.drawString(margin, height - 14 * mm, "Sahilli")
    pdf.setFont(body, 9.5)
    pdf.drawString(margin, height - 20 * mm, "Fiche de préparation — Déclaration RNE-F-005")
    pdf.setFont(body, 8.5)
    pdf.drawRightString(
        width - margin, height - 14 * mm, shape_arabic("ورقة تحضير — تصريح")
    )
    pdf.drawRightString(
        width - margin, height - 20 * mm, f"Généré le {generated_on:%d/%m/%Y}"
    )

    y = height - 38 * mm

    # ---- the disclaimer that keeps this honest ----------------------------
    pdf.setFillColor(colors.HexColor("#FBF1E3"))
    pdf.rect(margin, y - 16 * mm, width - 2 * margin, 16 * mm, fill=1, stroke=0)
    pdf.setFillColor(colors.HexColor("#8F5206"))
    pdf.setFont(bold, 9)
    pdf.drawString(margin + 4 * mm, y - 6 * mm, "Ce document n'est pas un dépôt officiel.")
    pdf.setFont(body, 8.2)
    pdf.drawString(
        margin + 4 * mm,
        y - 10 * mm,
        "Depuis le 1er juillet 2026, la déclaration se remplit en ligne sur le portail du RNE,",
    )
    pdf.drawString(
        margin + 4 * mm,
        y - 13.5 * mm,
        "signée par identité numérique. Recopiez ces informations sur le portail.",
    )
    y -= 24 * mm

    # ---- what is being declared -------------------------------------------
    y = _section(pdf, margin, y, width, "Démarche déclarée", "الإجراء المصرّح به", bold, body)
    y = _row(pdf, margin, y, width, "Type de modification",
             submission.get("modification_type_fr") or completeness.get("display_name_fr", "—"),
             body, bold)
    y = _row(pdf, margin, y, width, "Référence",
             completeness.get("official_reference", "—"), body, bold)
    y -= 4 * mm

    # ---- the declaration itself -------------------------------------------
    y = _section(pdf, margin, y, width, "Données de la déclaration", "بيانات التصريح", bold, body)
    for spec in DECLARATION_FIELDS:
        value = str(declaration.get(spec.name) or "").strip()
        if not value and not spec.required:
            continue
        y = _row(
            pdf, margin, y, width,
            f"{spec.label_fr}  ·  {shape_arabic(spec.label_ar)}",
            value or "— à compléter —",
            body, bold, muted=not value,
        )
        if y < 40 * mm:
            pdf.showPage()
            y = height - margin
    y -= 4 * mm

    # ---- documents prepared -------------------------------------------------
    documents = submission.get("documents") or {}
    if documents:
        y = _section(pdf, margin, y, width, "Pièces préparées", "الوثائق المحضَّرة", bold, body)
        from app.services.rules_engine import DOCUMENT_LABELS

        for key in documents:
            label = DOCUMENT_LABELS.get(key, {}).get("fr", key)
            y = _row(pdf, margin, y, width, label, "fournie", body, bold)
            if y < 30 * mm:
                pdf.showPage()
                y = height - margin

    # ---- footer -------------------------------------------------------------
    pdf.setFont(body, 7.5)
    pdf.setFillColor(MUTED)
    pdf.drawCentredString(
        width / 2, 12 * mm,
        "Sahilli — service indépendant de pré-validation. Ne remplace pas le portail du RNE.",
    )

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def _section(pdf, margin, y, width, title_fr, title_ar, bold, body):
    pdf.setFillColor(TEAL)
    pdf.setFont(bold, 10.5)
    pdf.drawString(margin, y, title_fr)
    pdf.setFont(body, 9)
    pdf.setFillColor(MUTED)
    pdf.drawRightString(width - margin, y, shape_arabic(title_ar))
    pdf.setStrokeColor(LINE)
    pdf.setLineWidth(0.6)
    pdf.line(margin, y - 2.5 * mm, width - margin, y - 2.5 * mm)
    return y - 9 * mm


def _row(pdf, margin, y, width, label, value, body, bold, muted=False):
    pdf.setFont(body, 8.6)
    pdf.setFillColor(MUTED)
    pdf.drawString(margin, y, shape_arabic(label)[:78])
    pdf.setFont(bold, 9.4)
    pdf.setFillColor(colors.HexColor("#8F5206") if muted else INK)
    pdf.drawRightString(width - margin, y, shape_arabic(str(value))[:60])
    return y - 7.5 * mm
