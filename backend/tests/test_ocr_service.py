"""OCR service tests.

The live vision call is mocked: these assert our prompt/parse/fallback wiring,
not Mistral's accuracy.
"""

from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image, ImageDraw

from app.services.ocr_service import (
    OCRService,
    _fields_from_plain_text,
    _parse_json_object,
)


def _sample_png(lines: list[str]) -> bytes:
    image = Image.new("RGB", (900, 460), "white")
    draw = ImageDraw.Draw(image)
    for index, line in enumerate(lines):
        draw.text((40, 40 + index * 60), line, fill="black")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


PV_LINES = [
    "PROCES-VERBAL DE L'ASSEMBLEE GENERALE",
    "Societe: SARL EXEMPLE TUNISIE",
    "Date de la decision: 12/06/2026",
    "Nouveau representant legal: Amine Ben Salah",
    "CIN: 12345678",
]

MODEL_JSON = """```json
{
  "full_text": "PROCES-VERBAL ...",
  "id_number": "12345678",
  "person_name": "Amine Ben Salah",
  "company_name": "SARL EXEMPLE TUNISIE",
  "company_id": null,
  "issue_date": null,
  "decision_date": "2026-06-12",
  "signature_date": "2026-06-12",
  "has_signature": true,
  "other_id_numbers": [],
  "notes": null
}
```"""


def _mock_mistral(payload: str) -> MagicMock:
    client = MagicMock()
    message = MagicMock()
    message.content = payload
    client.chat.complete.return_value = MagicMock(choices=[MagicMock(message=message)])
    return client


@patch("app.services.ocr_service.settings")
def test_vision_extraction_parses_fenced_json(mock_settings) -> None:
    mock_settings.mistral_api_key = "test-key"
    mock_settings.vision_model = "mistral-large-2512"

    service = OCRService(model="mistral-large-2512")
    with (
        patch.object(OCRService, "_resolve_vision_model", return_value="mistral-large-2512"),
        patch("mistralai.client.Mistral", return_value=_mock_mistral(MODEL_JSON)),
    ):
        result = service.extract(_sample_png(PV_LINES), "pv.png", "general_assembly_pv")

    assert result.degraded is False
    assert result.engine == "mistral:mistral-large-2512"
    assert result.fields["id_number"] == "12345678"
    assert result.fields["decision_date"] == "2026-06-12"
    assert result.document_type == "general_assembly_pv"


@patch("app.services.ocr_service.settings")
def test_prompt_is_specialised_per_document_type(mock_settings) -> None:
    """The caller-supplied document type must reach the model's prompt."""
    mock_settings.mistral_api_key = "test-key"
    mock_settings.vision_model = "mistral-large-2512"

    client = _mock_mistral(MODEL_JSON)
    service = OCRService(model="mistral-large-2512")
    with (
        patch.object(OCRService, "_resolve_vision_model", return_value="mistral-large-2512"),
        patch("mistralai.client.Mistral", return_value=client),
    ):
        service.extract(_sample_png(PV_LINES), "id.png", "national_id")

    sent = client.chat.complete.call_args.kwargs["messages"][0]["content"]
    prompt = sent[0]["text"]
    assert "national_id" in prompt
    assert "CIN" in prompt  # the national_id hint, not the PV one
    assert sent[1]["type"] == "image_url"


@patch("app.services.ocr_service.settings")
def test_api_failure_falls_back_to_local_engine(mock_settings) -> None:
    mock_settings.mistral_api_key = "test-key"
    mock_settings.vision_model = "mistral-large-2512"

    with (
        patch.object(OCRService, "_resolve_vision_model", return_value="m"),
        patch("mistralai.client.Mistral", side_effect=RuntimeError("api down")),
    ):
        result = OCRService().extract(_sample_png(PV_LINES), "pv.png", "general_assembly_pv")

    # Either Tesseract ran, or it is not installed -- both are "degraded",
    # and neither may raise.
    assert result.degraded is True
    assert result.engine in {"tesseract", "none"}


@patch("app.services.ocr_service.settings")
def test_no_api_key_goes_straight_to_local(mock_settings) -> None:
    mock_settings.mistral_api_key = ""
    mock_settings.vision_model = "mistral-large-2512"

    result = OCRService().extract(_sample_png(PV_LINES), "pv.png", "general_assembly_pv")
    assert result.degraded is True


def test_undecodable_upload_returns_error_not_exception() -> None:
    result = OCRService().extract(b"", "empty.pdf", "national_id")
    assert result.error is not None
    assert result.degraded is True


def test_pdf_is_rasterised_to_pages() -> None:
    """Exercises the real pdf2image/Poppler path."""
    pdf_buffer = BytesIO()
    Image.open(BytesIO(_sample_png(PV_LINES))).convert("RGB").save(
        pdf_buffer, format="PDF"
    )
    pages = OCRService()._to_images(pdf_buffer.getvalue(), "pv.pdf")
    assert len(pages) == 1
    assert pages[0][:4] == b"\x89PNG"


@pytest.mark.parametrize(
    "raw",
    ['{"id_number": "1"}', '```json\n{"id_number": "1"}\n```', 'text {"id_number": "1"} tail'],
)
def test_parse_json_object_tolerates_wrappers(raw: str) -> None:
    assert _parse_json_object(raw)["id_number"] == "1"


def test_parse_json_object_returns_empty_on_garbage() -> None:
    assert _parse_json_object("no json at all") == {}


def test_plain_text_fallback_picks_up_cin_and_dates() -> None:
    fields = _fields_from_plain_text("CIN: 12345678 autre 87654321 le 12/06/2026")
    assert fields["id_number"] == "12345678"
    assert fields["other_id_numbers"] == ["87654321"]
    assert fields["issue_date"] == "2026-06-12"
