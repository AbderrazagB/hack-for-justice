# Sahilli — سهّلي

> **Sahilli** (Tunisian dialect for *"make it easy for me"*) is an AI-powered
> pre-validation and institutional review platform for Tunisia's National
> Business Registry (RNE).

MSMEs lose weeks to RNE filings that get rejected for avoidable reasons: a
missing *procès-verbal*, an Extrait RNE that has gone stale, an ID number that
doesn't match across documents, a decision filed past its legal deadline.
Sahilli catches those problems **before** submission, and gives RNE officers a
triage dashboard that surfaces exactly what is wrong with each incoming request.

Sahilli is **not** a replacement for RNE's filing portal. It is a validation
layer that sits in front of it.

**Workflow covered:** *Modification Entreprise* / **تحيين مؤسسة** — specifically
*changement de représentant légal* (official checklist reference **RNE-M-005**).

## Tech stack

- **Backend:** FastAPI, Python 3.11+, managed with uv
- **Frontend:** Next.js (App Router), TypeScript, Tailwind CSS
- **Vector database:** Qdrant (self-hosted)
- **Embeddings:** BAAI/bge-m3 via HuggingFace Text Embeddings Inference (self-hosted)
- **OCR / vision:** Pixtral (Apache-2.0, open-weight) via Mistral's API, with a
  local Tesseract fallback
- **LLM reasoning:** Mistral with a Google Gemini fallback

## Local AI Infrastructure

Sahilli is designed to run against **locally self-hosted Qdrant and BGE-M3
embedding containers rather than managed cloud services.** This is a deliberate
architecture choice, not a hackathon shortcut: aside from the LLM reasoning
layer, the entire platform can eventually be **fully self-hosted by an
institution like RNE on its own infrastructure**, so that citizens' and
companies' filing documents never leave national infrastructure. Data
sovereignty is a hard requirement for a registry, and the retrieval stack is
built that way from day one.

The LLM reasoning layer (Mistral / Gemini / Pixtral) currently runs on vendor
APIs for hackathon speed. That layer has a credible self-hosting path too —
Pixtral-12B is Apache-2.0 licensed and can be run locally — so "sovereign
Sahilli" is an incremental step, not a rewrite.

### What this repo expects to already be running

`docker-compose.yml` deliberately **does not define** Qdrant or an embedding
service. It expects them to already exist on the host, and the backend simply
points at them:

| Service | Image | Host port | Used for |
|---|---|---|---|
| Qdrant | `qdrant/qdrant` | **6333** (HTTP), 6334 (gRPC) | `rne_procedures` collection |
| Embeddings | `ghcr.io/huggingface/text-embeddings-inference` (`--model-id BAAI/bge-m3`) | **8090** | 1024-dim vectors |

Configure via `.env`:

```bash
QDRANT_URL=http://localhost:6333
EMBEDDING_SERVICE_URL=http://localhost:8090
EMBEDDING_DIM=1024
```

**If your ports differ,** change those two variables — that's the only wiring
needed. Nothing else in the codebase hardcodes a port. When running the backend
inside Docker, use `http://host.docker.internal:<port>` instead of `localhost`
(compose already sets this up via `extra_hosts`). Leaving `QDRANT_URL` blank
falls back to an in-memory Qdrant, which is enough to run the unit tests but
loses all data on restart.

### Embedding API shape

The TEI container answers on two endpoints. Sahilli uses the **TEI-native
`POST /embed`**:

```bash
curl -X POST http://localhost:8090/embed \
  -H 'Content-Type: application/json' \
  -d '{"inputs": ["premier document", "الوثيقة الثانية"]}'
# -> [[0.008, -0.024, ...], [...]]   two 1024-dim vectors
```

The OpenAI-compatible `POST /v1/embeddings` (`{"input": ..., "model": ...}`)
also works and returns the usual `{"data":[{"embedding":[...]}]}` envelope. We
chose `/embed` because it batches a list of strings in one round-trip, returns
a bare list of vectors with no envelope to unwrap, and needs no `model` field
kept in sync with however the server was launched. This is documented in
`backend/app/services/embedding_service.py`.

### Fallback: if you don't have these containers yet

This is the fallback path, not the primary one. If the host has no Qdrant or
embedding server, start your own:

```bash
# Qdrant
docker run -d --name sahilli-qdrant \
  -p 6333:6333 -p 6334:6334 \
  -v "$(pwd)/qdrant_storage:/qdrant/storage" \
  qdrant/qdrant:v1.15.1

# BGE-M3 embeddings (CPU build; drop `-cpu` and add `--gpus all` for NVIDIA)
docker run -d --name sahilli-embeddings \
  -p 8090:80 \
  -v "$(pwd)/hf_cache:/data" \
  ghcr.io/huggingface/text-embeddings-inference:cpu-1.8 \
  --model-id BAAI/bge-m3 --port 80
```

First start downloads the BGE-M3 weights (~2.2 GB) — give it a few minutes, and
check readiness with `curl http://localhost:8090/health`.

> **Note on qdrant-client versions.** The client is pinned to `>=1.15,<1.17` to
> stay within Qdrant's supported client/server version skew. If you run a newer
> server, bump the pin in `backend/pyproject.toml` to match.

## Prerequisites

- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/) installed
- Node.js 20.9 or newer (required by the current Next.js release)
- Docker and Docker Compose
- **Poppler** (`pdf2image` needs it to rasterise PDF pages):
  `sudo apt install poppler-utils`
- **Tesseract** (local OCR fallback):
  `sudo apt install tesseract-ocr tesseract-ocr-fra tesseract-ocr-ara`

## Setup

1. Clone the repository and enter it:

   ```bash
   git clone <repository-url>
   cd sahilli
   ```

2. Create your local environment file and add API keys:

   ```bash
   cp .env.example .env
   ```

3. Install backend and frontend dependencies:

   ```bash
   ./scripts/setup.sh
   ```

4. Seed the RAG grounding corpus into Qdrant (one-off):

   ```bash
   cd backend && uv run python ../scripts/seed_rag.py
   ```

5. Start the backend:

   ```bash
   cd backend
   uv run uvicorn app.main:app --reload
   ```

6. In another terminal, start the frontend:

   ```bash
   cd frontend
   npm run dev
   ```

Open http://localhost:3000. The FastAPI docs are at http://localhost:8000/docs.

To run backend + frontend with Docker instead (Qdrant and embeddings stay
external, as described above):

```bash
docker-compose up --build
```

## Project structure

```text
backend/    FastAPI application, integrations, services, and tests
frontend/   Next.js web application and shared UI code
data/       Raw, processed, schema, seed, and generated demo data
prompts/    Version-controlled LLM prompts and examples
notebooks/  Exploratory notebooks
docs/       Architecture notes and demo guide
scripts/    Setup, RAG seeding, and demo-data helpers
```

## Team

- [Name] — [Role]
