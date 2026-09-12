# Document Extraction Prompt

**Source of truth: `backend/app/services/ocr_service.py`** (`DOCUMENT_TYPE_HINTS`
and `_EXTRACTION_SCHEMA`). This file documents it for review; edit the code,
then update this file.

Sent to an open-weight Apache-2.0 vision model with the rendered page images
attached. The document type is always supplied by the caller, never inferred.

```text
You are extracting data from an official Tunisian administrative document for a
business-registry filing.

DOCUMENT TYPE: {document_type}
{type-specific hint}

The document may be in French, Arabic, or both. Read all pages.
Return ONLY a JSON object, no prose and no markdown fence, matching:
{schema}

Rules: use null for anything not present -- never guess or invent a value.
Normalise every date to YYYY-MM-DD. Strip spaces and separators from ID numbers.
```

## Schema

```json
{
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
}
```

## Per-type hints

| `document_type` | Focus |
|---|---|
| `national_id` | 8-digit CIN, name in both scripts, date and place of birth/issue |
| `company_statutes` | Company name, legal form, address, capital, **every named representative and their ID** |
| `rne_extract` | Company name, RNE identifier, **issue date of the extract itself**, current representative |
| `tax_registration_card` | Tax identification number, company name, activity, registration date |
| `general_assembly_pv` | **Decision date**, outgoing and incoming representative, incoming ID, whether signed and when |

## Why the rules are phrased this way

- **`null` over a guess.** A hallucinated CIN would produce a false mismatch
  accusation against a real applicant. A `null` produces `INDETERMINATE`, which
  asks a human to look. The asymmetry is deliberate.
- **Normalised dates and IDs.** The rules engine compares these across
  documents; `12 345 678` and `12345678` must not read as a mismatch.
- **`other_id_numbers`.** The cross-document check compares every ID a document
  mentions, not just the primary one.
- **The flat schema is shared across types.** `rules_engine` and `scoring` read
  the same field names regardless of which document produced them.

## Fallback

Tesseract produces raw text with no layout, so no schema applies. A conservative
regex picks up only unambiguous patterns (8-digit CINs, ISO and DD/MM/YYYY
dates) and leaves everything else null. Those results are always marked
`degraded=True`.
