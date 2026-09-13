# Sahilli — Demo Script

## Before you start

```bash
# 1. External containers (Qdrant + BGE-M3) must be running
docker ps | grep -E "qdrant|embeddings"

# 2. Seed the RAG corpus (once)
cd backend && uv run python ../scripts/seed_rag.py

# 3. Backend
cd backend && uv run uvicorn app.main:app --reload

# 4. Frontend
cd frontend && npm run dev

# 5. Fill the officer queue
./scripts/seed_demo_data.sh
```

> **Check first:** `MISTRAL_API_KEY` must be set, or `tesseract` installed.
> With neither, OCR extracts nothing and every case reads NEEDS_REVIEW —
> the clean/broken contrast that carries the demo disappears.

## Demo Flow

**1. The problem (30s).** An MSME changes its legal representative. Five
documents, a one-month legal deadline, and a rejection costs weeks. Nobody finds
out what was wrong until the registry says no.

**2. The MSME side (2 min).** `localhost:3000/msme` → *Modification Entreprise*.
The checklist is the registry's own (RNE-M-005). Attach the **DEMO-001**
documents — deliberately leave one out first to show the live checklist naming
what's missing. Hit *Vérifier*.

Sahilli reports `INCOMPLETE` and names the missing piece. Attach it and re-run:
now `NEEDS_REVIEW`, with the real finding — *"Le numéro de CIN de la carte
d'identité (X) ne correspond pas au numéro cité dans le procès-verbal (Y)"*.
That is a cross-document check no single-document OCR tool catches.

**2b. The evidence (30 s).** Click **Voir sur la pièce** under that finding.
Both pages open with each number outlined where it actually appears. The
verdict stops asking to be believed.

**3. The grounded assistant (1 min).** Open it from **Besoin d'aide ?** in the
bottom-right -- it follows you across the applicant-facing app, and answers about
the procedure even before anything is uploaded. Ask *"Quel est le délai légal pour
déposer ?"* The answer cites **loi 52-2018** — pulled from the corpus, not the
model's memory. Switch to **AR** and ask again. Point at the citation chips:
every procedural claim traces to official text, and if retrieval fails the panel
says the answer is unsourced rather than bluffing.

**4. The officer side (2 min).** `localhost:3000/admin`. Eight filings, flag
counts visible in the queue. Open **DEMO-003** — filed 74 days after the
decision. The flag states the overdue count *and* the penalty exposure (half the
standard fee per started month). Extracted fields sit beside the original scan;
click a flag and it jumps to the implicated document.

Decide *Demander une correction* with a note. Watch the stats panel recompute —
average decision time and flag rate are live, not hardcoded.

**5. The close (30s).** The pitch: everything except the LLM reasoning layer
already runs on self-hosted infrastructure — Qdrant and BGE-M3 in local
containers — and the OCR model is Apache-2.0 open-weight. RNE can take this
in-house without a licensing negotiation.

## Talking Points

- **The LLM never decides.** A deterministic rules engine does; the model only
  explains. Two runs on the same filing never disagree, and an officer can
  always be told which rule fired and why.
- **We won't accuse someone we can't read.** An unreadable scan returns
  `INDETERMINATE`, not `FAIL` — a warning for the officer, never "your ID
  doesn't match".
- **Law vs. practice, kept separate.** The one-month deadline is statutory and sits
  in the cited corpus. The 90-day Extrait freshness rule is registry practice
  and is deliberately kept out of it, so it's never cited as law.
- **Bilingual by construction.** Every rule reason, flag and document label
  carries FR and AR, because the applicants do.
- **Data sovereignty is the roadmap, not a slogan.** Retrieval is already
  self-hosted; the OCR weights are Apache-2.0 and downloadable today.

## If something breaks

| Symptom | Cause | Fix |
|---|---|---|
| Every case reads NEEDS_REVIEW, no fields | No OCR engine | Set `MISTRAL_API_KEY`, or `sudo apt install tesseract-ocr tesseract-ocr-fra tesseract-ocr-ara` |
| Assistant says "réponse non sourcée" | Corpus unseeded or embeddings down | `docker start backend-embeddings-1`, then `uv run python ../scripts/seed_rag.py` |
| Queue empty | No demo data | `./scripts/seed_demo_data.sh` |
| "Impossible de joindre l'API" | Backend not running | `cd backend && uv run uvicorn app.main:app --reload` |
