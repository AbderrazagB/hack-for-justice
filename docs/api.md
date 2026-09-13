# Sahilli API — pre-validation as a service

Written for engineers integrating Sahilli into their own product.

You send the documents a client has already given you. You get back whether
Tunisia's National Business Registry would reject the filing, and why — before
anyone submits it.

Nothing is filed. This answers a question about a dossier; it does not lodge it.

```
POST /v1/validate  →  { "accepted": false, "findings": [ … ] }
```

## Who this is for

- **Banks and fintechs** onboarding a company: confirm the file is filable
  before opening an account against it.
- **Accountants and legal practices** filing on behalf of clients: catch the
  rejection in your own software, at the point the client is still on the phone.
- **Legal-tech and e-gov platforms**: embed pre-validation without building a
  rules engine or an OCR pipeline.

## Authentication

A key per integration, in a standard bearer header.

```bash
curl -H "Authorization: Bearer sk_sahilli_…" https://api.sahilli.tn/v1/transactions
```

`X-API-Key: sk_sahilli_…` is accepted too. Keys are shown once at issue and
stored only as a SHA-256 hash, so a lost key is reissued rather than recovered.
Revoking one takes effect on the next call.

Every response carries your consumption:

```json
"quota": { "monthly_quota": 1000, "used": 37, "remaining": 963 }
```

Exceeding it returns `429` with `Retry-After`. The period rolls at the turn of
the month.

## `GET /v1/transactions`

Call this first. It returns each procedure, the document `key`s it expects, and
the rules it applies — the identifiers every other call uses.

```json
[
  {
    "transaction_type": "RNE_MODIFICATION_ENTREPRISE",
    "official_reference": "RNE-M-005",
    "required_documents": [
      { "key": "id_new_representative", "label_fr": "Carte d'identité nationale…" }
    ],
    "checks": ["documents_match_their_type", "id_number_matches_across_documents", "…"],
    "declaration_fields": [
      { "name": "declarant_id", "required": true, "cross_checked": true }
    ]
  }
]
```

`cross_checked` marks the declaration fields that are compared against the
documents. The others are recorded, not verified — and the API says so rather
than implying otherwise.

## `POST /v1/validate`

`multipart/form-data`. One `files` part per document, one `document_types` part
per file, in the same order.

```bash
curl -X POST https://api.sahilli.tn/v1/validate \
  -H "Authorization: Bearer $SAHILLI_KEY" \
  -F "transaction_type=RNE_MODIFICATION_ENTREPRISE" \
  -F "files=@cin.png"        -F "document_types=id_new_representative" \
  -F "files=@statuts.pdf"    -F "document_types=company_statutes" \
  -F "files=@extrait.pdf"    -F "document_types=rne_extract" \
  -F "files=@fiscale.pdf"    -F "document_types=tax_registration_card" \
  -F "files=@pv.pdf"         -F "document_types=general_assembly_pv" \
  -F "submitted_at=2026-09-13" \
  -F 'declaration={"declarant_id":"31790642","unique_identifier":"A0000001"}'
```

| Field | | |
|---|---|---|
| `transaction_type` | required | from `/v1/transactions` |
| `files` / `document_types` | required | parallel arrays, ≤ 12 documents |
| `declaration` | optional | RNE-F-005 answers as JSON. Omit it and the declaration cross-check does not run — and appears in `skipped_checks` saying so |
| `submitted_at` | optional | `YYYY-MM-DD`, defaults to today. Deadlines are computed against it |
| `company_type`, `fiscal_year_end` | optional | needed by the annual-filing rules |

### The response

```json
{
  "validation_id": "b68f4a80d907",
  "accepted": false,
  "status": "NEEDS_REVIEW",
  "summary": { "total": 3, "errors": 3, "warnings": 0, "info": 0 },
  "missing_documents": [],
  "checks": [ { "name": "pv_is_signed", "outcome": "FAIL", "reason_fr": "…" } ],
  "skipped_checks": [ { "name": "…", "reason_fr": "…" } ],
  "findings": [
    {
      "code": "id_number_matches_across_documents",
      "severity": "ERROR",
      "message_fr": "Le numéro de CIN de la carte d'identité (31790642) ne correspond pas…",
      "documents": [ { "key": "id_new_representative" }, { "key": "general_assembly_pv" } ]
    }
  ],
  "deadline": {
    "date": "2026-04-12", "days_overdue": 154,
    "penalty_estimate_tnd": 150, "article": "loi 52-2018, art. 26"
  }
}
```

**Branch on `accepted`.** It is true only when every required document is
present and every rule passed.

`status` distinguishes the two ways that fails: `INCOMPLETE` (a document is
missing) from `NEEDS_REVIEW` (a rule failed, or could not be decided).

Three outcomes per rule, and the third is not a failure:

| `outcome` | Means |
|---|---|
| `PASS` | The rule ran and found nothing wrong |
| `FAIL` | The rule ran and found a problem |
| `INDETERMINATE` | The rule could not decide — an unreadable page, a value absent on both sides |

`skipped_checks` lists rules that did not run at all, with the reason. A rule
missing from `checks` and absent here would read as one that passed, which is
the failure mode this field exists to prevent.

### Timing

Synchronous, and every page is read. Budget roughly **fifteen seconds per
document**. A five-document dossier takes around a minute and a half; set your
client timeout accordingly.

## `GET /v1/validations/{validation_id}`

The same response, for a validation this key's owner produced earlier. A
validation belongs to the integration that created it: another key gets `403`,
and dossiers filed through the Sahilli web application are not readable over the
API at all.

## `GET /v1/usage`

This key's consumption, for your own dashboard. No secret is returned.

## Errors

| Code | |
|---|---|
| `400` | Malformed request — mismatched arrays, unknown `document_types`, bad `declaration` JSON |
| `401` | Missing, unknown or revoked key |
| `403` | The validation belongs to another account |
| `404` | Unknown `transaction_type` or `validation_id` |
| `413` | A file over 10 MB, or a batch over 40 MB |
| `429` | Monthly quota reached; see `Retry-After` |

## Issuing keys

```bash
cd backend && uv run python ../scripts/create_api_key.py issue "Banque X" ops@banque.tn
cd backend && uv run python ../scripts/create_api_key.py list
cd backend && uv run python ../scripts/create_api_key.py revoke sk_sahilli_…
```

`--quota N` sets the monthly allowance; it defaults to 1000.

## What is guaranteed

`/v1` is a contract. Fields are added, never removed or repurposed, without a
`/v2`.

Two things worth knowing before you build on it:

- **A verdict comes from deterministic rules, never a language model.** Models
  read documents and explain results; they do not decide whether a filing is
  valid. The same documents produce the same verdict.
- **Uncertainty is reported as uncertainty.** A check that could not be made
  returns `INDETERMINATE` or appears in `skipped_checks`. It is never silently
  treated as a pass.

The interactive reference is at `/docs`, generated from the same models that
serve the responses.
