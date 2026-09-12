# Sahilli — Architecture

## Overview

Sahilli is a **pre-validation layer in front of the RNE**, not a replacement for
the registry's filing portal. An MSME assembles a *Modification Entreprise*
(changement de représentant légal, checklist **RNE-M-005**) here first; Sahilli
reads the documents, decides deterministically whether the filing would survive
intake, and explains any problems in French or Arabic. RNE officers get the same
findings as a triage queue.

The central design commitment: **the LLM never decides whether a filing is
valid.** A deterministic rules engine does. The model only rewrites those
findings into language a non-lawyer can act on, grounded in retrieved official
text. That keeps the answer identical across two runs, keeps it explainable to
an officer, and keeps a hallucinated deadline out of a citizen's compliance
decision.

## Components

```
  MSME (/msme)                          Officer (/admin)
        │                                      │
        └──────────────┐        ┌──────────────┘
                       ▼        ▼
                  FastAPI (app/api)
                       │
     ┌─────────────────┼──────────────────┬───────────────────┐
     ▼                 ▼                  ▼                   ▼
 ocr_service     rules_engine          scoring         retrieval_service
 (vision LLM      TRANSACTION_RULES    Flags for        RAG over curated
  + Tesseract)    = source of truth    the dashboard    RNE text
     │                                                        │
     ▼                                                        ▼
 Mistral API                                    Qdrant  ←──  BGE-M3 (TEI)
 (external)                                     (self-hosted, external)
```

| Module | Responsibility |
|---|---|
| `app/api/submissions.py` | Intake, officer queue, review actions, stats, document serving |
| `app/api/assistant.py` | Grounded FR/AR explanation |
| `app/services/ocr_service.py` | Document → structured fields (vision LLM, Tesseract fallback) |
| `app/services/rules_engine.py` | `TRANSACTION_RULES` + `check_completeness` — **the** definition of "complete" |
| `app/services/scoring.py` | Check results → human-readable flags. Adds no rules of its own |
| `app/services/retrieval_service.py` | Embed + search the curated RNE corpus |
| `app/core/vector_store.py` | Qdrant wrapper (external container) |
| `app/services/embedding_service.py` | HTTP client for the external BGE-M3 container |
| `app/core/llm_client.py` | Mistral primary, Gemini fallback |
| `app/models/submission.py` | Submission model + JSON-backed store |

## Data Flow

**Submission.** `POST /transactions/{type}/submissions` receives files plus a
parallel list of document types — types are always supplied by the caller, never
guessed, so the extraction prompt can be specialised per document. PDFs are
rasterised (Poppler, 200 DPI, capped at 5 pages). Each page goes to the vision
model with a strict JSON schema that requires `null` over a guess. `pypdf` is
available for text-layer PDFs; the current path rasterises everything for
uniformity.

Extracted fields go to `check_completeness`, which verifies the five required
documents are present and runs five declared checks. Each check returns
`PASS`, `FAIL`, or `INDETERMINATE` — the third exists so an unreadable scan is
never reported as a violation. `scoring.flags_from_result` converts those into
flags carrying the actual values in dispute.

Status resolution: any missing document → `INCOMPLETE`; otherwise any `FAIL` or
`INDETERMINATE` → `NEEDS_REVIEW`; otherwise `COMPLETE`. A `COMPLETE` filing is
stored as `PRE_VALIDATED`.

**Explanation.** `POST /assistant/explain` builds its retrieval query *from the
problems actually found*, which is what pulls the deadline passage for a late
filing and the checklist passage for a missing document. The prompt carries two
blocks: the authoritative verdict, and the retrieved passages as the only
permitted source of procedural facts. If retrieval returns nothing, or the
provider fails, the endpoint returns the deterministic verdict and sets
`grounded: false` rather than letting the model improvise law.

**Review.** `POST /submissions/{id}/review` appends a decision and moves the
status. History accumulates; stats derive from it live.

## Deliberate choices

- **Self-hosted retrieval.** Qdrant and BGE-M3 run as local containers, not
  managed services, so RNE could eventually run the retrieval stack on its own
  hardware. See README → Local AI Infrastructure.
- **Open-weight OCR.** Mistral's `mistral-ocr-*` product is proprietary;
  self-hosting it requires a commercial licence. Sahilli uses Apache-2.0
  open-weight multimodal models so the self-hosting path is real and free.
- **90 days is not law.** The Extrait freshness rule is a registry expectation,
  kept in the rules engine and deliberately *out* of the RAG corpus so the
  assistant never cites it to a user as statute. The 30-day deadline *is*
  statutory (Law 52-2018) and is in the corpus.
- **JSON storage.** Adequate for a hackathon, survives restarts, atomic writes.
  Replacing it means reimplementing `SubmissionStore` alone.

## Known gaps

- OCR needs either `MISTRAL_API_KEY` or a local `tesseract` binary. With
  neither, every check returns `INDETERMINATE` and all filings read
  `NEEDS_REVIEW`.
- `UNDER_INSTITUTIONAL_REVIEW` exists in the tracker but nothing transitions
  into it yet; officers move filings straight from intake to a decision.
- Single transaction type. Adding another means one entry in
  `TRANSACTION_RULES` plus implementations for any new checks — the import-time
  guard refuses a rule that names an unimplemented check.
- No authentication. `/admin` is open; a real deployment needs officer identity
  rather than the free-text `officer` field.
