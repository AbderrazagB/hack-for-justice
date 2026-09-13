"""Find, on the page, the thing a flag is complaining about.

A verdict that says two documents disagree about a CIN is only convincing if
you can see both. This locates the disputed values inside the uploaded pages
and returns their boxes, so the reader can look at the pixels rather than
take the rules engine's word for it.

The boxes come from a separate Tesseract pass over the page, not from whatever
engine extracted the field. That is deliberate: Mistral's vision OCR returns
values with no coordinates, and asking a language model for pixel positions
invents them. Tesseract reports where it read each word, so a box here means
"these pixels say that", and a value it cannot find produces no box at all
rather than a plausible-looking rectangle over the wrong part of the page.

Boxes are fractions of the page, never pixels, so the overlay survives being
drawn at whatever width the layout gives it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from io import BytesIO
from typing import Any

# Rasterisation DPI for PDF pages. The page image endpoint must use the same
# value, or the boxes would be measured against a different raster than the one
# on screen.
PDF_DPI = 150

# Tesseract reports a confidence per word; below this it is usually noise.
MIN_WORD_CONFIDENCE = 30

# Values shorter than this match too much to be worth highlighting.
MIN_NEEDLE_LENGTH = 3

# RapidOCR scores a whole line 0..1.
MIN_LINE_CONFIDENCE = 0.4

# The ONNX session is expensive to build and safe to keep.
_RAPID: Any = None


@dataclass(frozen=True)
class Box:
    """A highlight, as fractions of the page's width and height."""

    x: float
    y: float
    width: float
    height: float
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "x": round(self.x, 5),
            "y": round(self.y, 5),
            "width": round(self.width, 5),
            "height": round(self.height, 5),
            "text": self.text,
        }


@dataclass
class PageEvidence:
    page: int
    boxes: list[Box] = field(default_factory=list)


def _normalise(token: str) -> str:
    """Compare on letters and digits only.

    OCR punctuation around a value is unreliable -- a CIN is read as "12345678",
    "12345678." or "n°12345678" depending on the crop -- and none of that
    changes whether the number is the one in dispute.
    """
    return re.sub(r"[^0-9a-z؀-ۿ]", "", token.casefold())


def needles_from_flag(flag: dict[str, Any], document_keys: set[str]) -> list[str]:
    """The values a flag is actually about, pulled out of its evidence.

    Evidence is a small dict of scalars and lists of dicts, so this walks it
    rather than special-casing every check. Document keys are skipped: they
    name where to look, not what to look for.
    """
    found: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif value is not None and not isinstance(value, bool):
            text = str(value).strip()
            if (
                len(_normalise(text)) >= MIN_NEEDLE_LENGTH
                and text not in document_keys
                and text not in found
            ):
                found.append(text)

    walk(flag.get("evidence") or {})
    return found


def _words(image_bytes: bytes) -> tuple[list[dict[str, Any]], int, int]:
    """Everything readable on the page, boxed, plus the page size.

    Tesseract first when its binary is installed: it reports word by word and
    handles Arabic. RapidOCR otherwise -- it is pip-installable with no system
    dependency, so the feature works on a machine where nobody can apt-get
    anything, which is most demo machines. It returns whole text lines rather
    than words, and `locate` matches against either shape.
    """
    try:
        return _tesseract_words(image_bytes)
    except Exception:  # noqa: BLE001 - not installed, or no language data
        return _rapidocr_lines(image_bytes)


def _tesseract_words(image_bytes: bytes) -> tuple[list[dict[str, Any]], int, int]:
    import pytesseract
    from PIL import Image

    image = Image.open(BytesIO(image_bytes))
    width, height = image.size
    data = pytesseract.image_to_data(
        image, output_type=pytesseract.Output.DICT, lang="fra+ara+eng"
    )

    words: list[dict[str, Any]] = []
    for index, text in enumerate(data["text"]):
        if not text.strip():
            continue
        try:
            confidence = float(data["conf"][index])
        except (TypeError, ValueError):
            confidence = -1.0
        if confidence < MIN_WORD_CONFIDENCE:
            continue
        words.append(
            {
                "text": text,
                "left": data["left"][index],
                "top": data["top"][index],
                "width": data["width"][index],
                "height": data["height"][index],
            }
        )
    if not words:
        raise RuntimeError("Tesseract read nothing; try the other engine")
    return words, width, height


def _rapidocr_lines(image_bytes: bytes) -> tuple[list[dict[str, Any]], int, int]:
    """Text lines and their boxes, from the ONNX engine."""
    import numpy as np
    from PIL import Image
    from rapidocr_onnxruntime import RapidOCR

    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    width, height = image.size

    global _RAPID
    if _RAPID is None:
        _RAPID = RapidOCR()

    result, _ = _RAPID(np.array(image))
    lines: list[dict[str, Any]] = []
    for box, text, score in result or []:
        if not text.strip() or float(score) < MIN_LINE_CONFIDENCE:
            continue
        xs = [point[0] for point in box]
        ys = [point[1] for point in box]
        lines.append(
            {
                "text": text,
                "left": int(min(xs)),
                "top": int(min(ys)),
                "width": int(max(xs) - min(xs)),
                "height": int(max(ys) - min(ys)),
            }
        )
    return lines, width, height


def locate(image_bytes: bytes, needles: list[str]) -> list[Box]:
    """Boxes for every needle found on the page.

    A needle of several words is matched across consecutive words, because
    Tesseract splits on whitespace and a name arrives as two entries.
    """
    if not needles:
        return []

    try:
        words, page_width, page_height = _words(image_bytes)
    except Exception:  # noqa: BLE001 - no Tesseract, or an unreadable page
        return []

    if not words or not page_width or not page_height:
        return []

    normalised = [_normalise(word["text"]) for word in words]
    boxes: list[Box] = []

    for needle in needles:
        parts = [_normalise(part) for part in needle.split()]
        parts = [part for part in parts if part]
        if not parts:
            continue

        # A line-based engine returns "CIN : 98797309" as one entry, so the
        # needle is also tried whole against a single entry; a word-based one
        # splits it, so consecutive entries are tried too.
        whole = "".join(parts)
        for index, entry in enumerate(normalised):
            if _matches([entry], [whole]):
                word = words[index]
                boxes.append(
                    Box(
                        x=word["left"] / page_width,
                        y=word["top"] / page_height,
                        width=word["width"] / page_width,
                        height=word["height"] / page_height,
                        text=word["text"],
                    )
                )

        if len(parts) == 1:
            continue

        for start in range(len(words) - len(parts) + 1):
            window = normalised[start : start + len(parts)]
            if not _matches(window, parts):
                continue

            spanned = words[start : start + len(parts)]
            left = min(word["left"] for word in spanned)
            top = min(word["top"] for word in spanned)
            right = max(word["left"] + word["width"] for word in spanned)
            bottom = max(word["top"] + word["height"] for word in spanned)

            boxes.append(
                Box(
                    x=left / page_width,
                    y=top / page_height,
                    width=(right - left) / page_width,
                    height=(bottom - top) / page_height,
                    text=" ".join(word["text"] for word in spanned),
                )
            )

    return _dedupe(boxes)


def _matches(window: list[str], parts: list[str]) -> bool:
    """Every word equal, or -- for a number -- present at a digit boundary.

    Normalising strips punctuation but not letters, so "n°98797309," arrives as
    "n98797309" and never compares equal. Allowing the value to sit inside the
    word fixes that, but a bare substring test would make "98797309" match
    "9879730912345" -- a different identifier, boxed as though it were the one
    in dispute. The boundary is what keeps the highlight honest.
    """
    if len(window) != len(parts):
        return False

    for read, wanted in zip(window, parts, strict=True):
        if read == wanted:
            continue
        if wanted.isdigit() and re.search(rf"(?<!\d){re.escape(wanted)}(?!\d)", read):
            continue
        return False
    return True


def _dedupe(boxes: list[Box]) -> list[Box]:
    seen: set[tuple[float, float, float, float]] = set()
    unique: list[Box] = []
    for box in boxes:
        key = (round(box.x, 4), round(box.y, 4), round(box.width, 4), round(box.height, 4))
        if key in seen:
            continue
        seen.add(key)
        unique.append(box)
    return unique


def render_page(content: bytes, page: int = 0) -> tuple[bytes, str]:
    """The page as an image, and its media type.

    An image file is its own page 0. A PDF is rasterised at PDF_DPI -- the same
    value the locator measured against, which is what keeps the boxes aligned
    with what the reader sees.
    """
    if content[:5] == b"%PDF-":
        from pdf2image import convert_from_bytes

        pages = convert_from_bytes(content, dpi=PDF_DPI, first_page=page + 1, last_page=page + 1)
        if not pages:
            raise ValueError(f"PDF has no page {page}")
        buffer = BytesIO()
        pages[0].save(buffer, format="PNG")
        return buffer.getvalue(), "image/png"

    if page != 0:
        raise ValueError("An image file has only page 0")
    return content, "image/png"


def page_count(content: bytes) -> int:
    if content[:5] != b"%PDF-":
        return 1
    try:
        from pypdf import PdfReader

        return len(PdfReader(BytesIO(content)).pages)
    except Exception:  # noqa: BLE001 - a broken PDF still has one page to show
        return 1
