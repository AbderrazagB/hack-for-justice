"""Document OCR for Sahilli.

WHY A VISION LLM AND NOT "MISTRAL OCR"
======================================
Mistral sells a dedicated OCR product (`mistral-ocr-*`). We deliberately do NOT
use it. It is a **proprietary commercial API and is not open-weight** -- an
enterprise self-hosting option exists, but only under separate commercial
licensing. That conflicts with Sahilli's core pitch to RNE: a registry handling
citizens' and companies' filing documents should be able to run the pipeline on
its own infrastructure, and "you may self-host if you sign a commercial
licence" is a materially weaker promise than "the weights are Apache-2.0, take
them".

So we run OCR through an **open-weight, Apache-2.0 licensed vision model** on
Mistral's API. Start on the API for hackathon speed; the path to running the
same weights on RNE hardware later is real and free, not a sales conversation.

MODEL SELECTION -- Pixtral is retired, and what we use instead
-------------------------------------------------------------
Sahilli was originally specced around **Pixtral-12B** (Apache-2.0, open-weight)
for exactly the reason above. Checking Mistral's live model documentation rather
than assuming the string turned out to matter: **Pixtral is deprecated and
retired from the API** -- `pixtral-12b-2409` retired 2025-12-02 and
`pixtral-large-2411` retired 2026-02-27. Hardcoding `pixtral-12b-2409` would
simply 404.

The rationale carries over cleanly to its successors, which are still
open-weight and still Apache-2.0:

  * `ministral-14b-2512`  -- Ministral 3 14B. Apache-2.0, open-weight, vision
    capable. Our default and the closest spiritual successor to Pixtral-12B:
    same licence, same order of size, genuinely self-hostable. Verified against
    the live API -- `mistral-large-2512` is NOT exposed on every account, so
    defaulting to it would break for some users.
  * `ministral-8b-2512`   -- Ministral 3 8B. Apache-2.0, lighter still; the
    cheapest realistic "sovereign deployment" target.

Because model IDs churn (as Pixtral proved), `_resolve_vision_model()` asks the
API which models actually exist and picks the first available from a preference
list, instead of trusting a constant. Override with VISION_MODEL in .env.

FALLBACK: TESSERACT
-------------------
`pytesseract` is wired as a fully local, zero-cost, zero-network fallback. It is
used when (a) no Mistral API key is configured, (b) the API call fails or the
account is out of quota, or (c) the caller explicitly forces it. Tesseract is
much weaker on layout, handwriting and mixed FR/AR script, and it returns raw
text with no structured fields -- so a Tesseract result is always marked
`degraded=True`, and callers should treat its extracted fields as unverified.
It exists so a live demo never hard-fails on a flaky conference network.
Requires the `tesseract-ocr` binary (plus `-fra` / `-ara` language packs);
if the binary is absent we degrade once more, to an empty result carrying an
explanatory error rather than raising.
"""

from __future__ import annotations

import base64
import json
import logging
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from app.core.config import settings
from app.core.retry import with_retry

logger = logging.getLogger(__name__)

# Preference order, best-quality first. All Apache-2.0 open-weight multimodal.
# Preference order, best-first, used when the configured model is unavailable.
# Apache-2.0 open-weight models lead, because a self-hostable default is the
# whole argument; the proprietary ones are last-resort so OCR still runs.
VISION_MODEL_PREFERENCE = [
    "ministral-14b-2512",   # Apache-2.0, open-weight, vision
    "ministral-8b-2512",    # Apache-2.0, open-weight, lighter
    "mistral-large-2512",   # Apache-2.0, not on every account
    "mistral-medium-latest",
    "mistral-small-latest",
]

# Document types Sahilli understands, with a hint that lightly specialises the
# extraction prompt. Keys match rules_engine.TRANSACTION_RULES required_documents.
DOCUMENT_TYPE_HINTS: dict[str, str] = {
    "national_id": (
        "A Tunisian national identity card (CIN / بطاقة تعريف وطنية). Extract the "
        "8-digit CIN number, full name in Latin and Arabic script if both appear, "
        "date of birth, and place of issue."
    ),
    "company_statutes": (
        "Company statutes (statuts de société). Extract the company name, legal "
        "form (SARL/SUARL/SA), registered address, share capital, and the full "
        "name and ID number of every named legal representative or manager."
    ),
    "rne_extract": (
        "An Extrait RNE (registry extract). Extract the company name, the RNE "
        "registration/unique identifier number, the issue date of the extract "
        "itself, and the currently registered legal representative."
    ),
    "tax_registration_card": (
        "A tax registration card / declaration of existence (patente, carte "
        "d'identifiant fiscal). Extract the tax identification number, company "
        "name, activity, and registration date."
    ),
    "general_assembly_pv": (
        "Minutes of a general assembly decision (procès-verbal). Extract the "
        "DATE OF THE DECISION, the company name, the outgoing representative, "
        "the newly appointed representative with their ID number, and whether "
        "the document carries signatures and a signature date."
    ),
    "general": "A business or administrative document.",
}

# Field names we ask the model to fill. Kept flat and stable so rules_engine and
# scoring can rely on them without knowing which document produced them.
_EXTRACTION_SCHEMA = """{
  "full_text": "all readable text, preserving line breaks",
  "id_number": "national ID / CIN number if present, digits only, else null",
  "person_name": "primary person named, else null",
  "company_name": "company name if present, else null",
  "company_id": "RNE or tax identifier if present, else null",
  "issue_date": "date this document was issued, YYYY-MM-DD, else null",
  "decision_date": "date of the decision recorded, YYYY-MM-DD, else null",
  "signature_date": "date next to signatures, YYYY-MM-DD, else null",
  "has_signature": true,
  "other_id_numbers": ["any other ID numbers appearing anywhere"],
  "notes": "anything illegible, missing, or suspicious"
}"""


@dataclass
class OCRResult:
    """Outcome of running OCR over one uploaded document."""

    document_type: str
    fields: dict[str, Any] = field(default_factory=dict)
    full_text: str = ""
    engine: str = ""           # "mistral:<model>" or "tesseract"
    degraded: bool = False     # True when produced by the weaker local fallback
    error: str | None = None
    page_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_type": self.document_type,
            "fields": self.fields,
            "full_text": self.full_text,
            "engine": self.engine,
            "degraded": self.degraded,
            "error": self.error,
            "page_count": self.page_count,
        }


class OCRService:
    """Extract structured data from uploaded identity and company documents."""

    def __init__(self, model: str | None = None) -> None:
        self._model_override = model or settings.vision_model

    # ---------------------------------------------------------------- public

    def extract(
        self,
        content: bytes,
        filename: str = "",
        document_type: str = "general",
        force_local: bool = False,
    ) -> OCRResult:
        """Extract structured fields from a document.

        `document_type` is supplied explicitly by the caller (never guessed) so
        the prompt can be specialised -- see DOCUMENT_TYPE_HINTS.
        """
        images = self._to_images(content, filename)
        if not images:
            return OCRResult(
                document_type=document_type,
                engine="none",
                degraded=True,
                error="Could not decode the upload as a PDF or an image.",
            )

        if not force_local and settings.mistral_api_key:
            try:
                return self._extract_with_vision_llm(images, document_type)
            except Exception as exc:  # noqa: BLE001 - any failure falls back to local OCR
                logger.warning("Vision OCR failed, falling back to Tesseract: %s", exc)

        return self._extract_with_tesseract(images, document_type)

    # ------------------------------------------------------------- rendering

    def _to_images(self, content: bytes, filename: str) -> list[bytes]:
        """Return one PNG per page. PDFs are rasterised via pdf2image/Poppler."""
        is_pdf = content[:5] == b"%PDF-" or filename.lower().endswith(".pdf")

        if not is_pdf:
            return [content]

        try:
            from io import BytesIO

            from pdf2image import convert_from_bytes

            # 200 DPI is a good accuracy/payload tradeoff for scanned admin
            # paperwork. Cap at 5 pages so one large PDF can't blow up a demo.
            pages = convert_from_bytes(content, dpi=200)[:5]
        except Exception as exc:  # noqa: BLE001
            logger.warning("PDF rasterisation failed (is Poppler installed?): %s", exc)
            return []

        rendered: list[bytes] = []
        for page in pages:
            buffer = BytesIO()
            page.save(buffer, format="PNG")
            rendered.append(buffer.getvalue())
        return rendered

    # ------------------------------------------------------------ vision LLM

    @staticmethod
    @lru_cache(maxsize=1)
    def _resolve_vision_model(preferred: str) -> str:
        """Pick a vision model that actually exists on the account.

        Model IDs churn -- Pixtral was retired out from under this project -- so
        we ask the API rather than trusting a constant. Falls back to the
        configured value if the listing is unavailable.
        """
        try:
            from mistralai.client import Mistral

            client = Mistral(api_key=settings.mistral_api_key)
            available = {m.id for m in client.models.list().data}
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not list Mistral models (%s); using %s", exc, preferred)
            return preferred

        for candidate in [preferred, *VISION_MODEL_PREFERENCE]:
            if candidate in available:
                return candidate

        logger.warning("No preferred vision model available; using %s", preferred)
        return preferred

    def _extract_with_vision_llm(
        self, images: list[bytes], document_type: str
    ) -> OCRResult:
        from mistralai.client import Mistral

        model = self._resolve_vision_model(self._model_override)
        hint = DOCUMENT_TYPE_HINTS.get(document_type, DOCUMENT_TYPE_HINTS["general"])

        prompt = (
            "You are extracting data from an official Tunisian administrative "
            "document for a business-registry filing.\n\n"
            f"DOCUMENT TYPE: {document_type}\n{hint}\n\n"
            "The document may be in French, Arabic, or both. Read all pages.\n"
            "Return ONLY a JSON object, no prose and no markdown fence, matching:\n"
            f"{_EXTRACTION_SCHEMA}\n\n"
            "Rules: use null for anything not present -- never guess or invent a "
            "value. Normalise every date to YYYY-MM-DD. Strip spaces and "
            "separators from ID numbers."
        )

        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for image in images:
            encoded = base64.b64encode(image).decode()
            content.append(
                {"type": "image_url", "image_url": f"data:image/png;base64,{encoded}"}
            )

        client = Mistral(api_key=settings.mistral_api_key)
        # One vision call per document means a submission can trip a per-minute
        # limit on its own; back off rather than degrade a readable document.
        response = with_retry(
            lambda: client.chat.complete(
                model=model,
                messages=[{"role": "user", "content": content}],
                temperature=0,
            ),
            description=f"vision OCR ({model})",
        )
        raw = response.choices[0].message.content
        text = raw if isinstance(raw, str) else str(raw)

        fields = _parse_json_object(text)
        return OCRResult(
            document_type=document_type,
            fields=fields,
            full_text=str(fields.get("full_text") or text),
            engine=f"mistral:{model}",
            degraded=False,
            page_count=len(images),
        )

    # -------------------------------------------------------------- fallback

    def _extract_with_tesseract(
        self, images: list[bytes], document_type: str
    ) -> OCRResult:
        """Local, offline OCR. Weaker: raw text only, so results are `degraded`."""
        try:
            from io import BytesIO

            import pytesseract
            from PIL import Image
        except Exception as exc:  # noqa: BLE001
            return OCRResult(
                document_type=document_type,
                engine="none",
                degraded=True,
                error=f"No OCR engine available: {exc}",
            )

        chunks: list[str] = []
        for image in images:
            try:
                # fra+ara covers Tunisian administrative paperwork; fall back to
                # the default language if those packs aren't installed.
                chunks.append(
                    pytesseract.image_to_string(
                        Image.open(BytesIO(image)), lang="fra+ara"
                    )
                )
            except pytesseract.TesseractError:
                chunks.append(pytesseract.image_to_string(Image.open(BytesIO(image))))
            except Exception as exc:  # noqa: BLE001 - binary missing, bad image, etc.
                return OCRResult(
                    document_type=document_type,
                    engine="none",
                    degraded=True,
                    error=(
                        f"Tesseract unavailable ({exc}). Install it with "
                        "`sudo apt install tesseract-ocr tesseract-ocr-fra "
                        "tesseract-ocr-ara`, or configure MISTRAL_API_KEY."
                    ),
                    page_count=len(images),
                )

        text = "\n".join(chunks).strip()
        return OCRResult(
            document_type=document_type,
            fields=_fields_from_plain_text(text),
            full_text=text,
            engine="tesseract",
            degraded=True,
            page_count=len(images),
        )


# --------------------------------------------------------------- helpers

def _parse_json_object(text: str) -> dict[str, Any]:
    """Pull a JSON object out of a model response, tolerating markdown fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.DOTALL)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}

    return parsed if isinstance(parsed, dict) else {}


def _fields_from_plain_text(text: str) -> dict[str, Any]:
    """Best-effort regex extraction over Tesseract's raw text.

    Deliberately conservative: Tesseract gives us no layout, so we only pick up
    unambiguous patterns (8-digit Tunisian CINs, ISO and DD/MM/YYYY dates) and
    leave everything else null for a human to confirm.
    """
    ids = re.findall(r"\b\d{8}\b", text)
    dates = re.findall(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    dates += [
        f"{y}-{m}-{d}"
        for d, m, y in re.findall(r"\b(\d{2})[/.](\d{2})[/.](\d{4})\b", text)
    ]

    return {
        "full_text": text,
        "id_number": ids[0] if ids else None,
        "person_name": None,
        "company_name": None,
        "company_id": None,
        "issue_date": dates[0] if dates else None,
        "decision_date": None,
        "signature_date": None,
        "has_signature": None,
        "other_id_numbers": ids[1:],
        "notes": "Extracted by local Tesseract fallback; fields are unverified.",
    }
