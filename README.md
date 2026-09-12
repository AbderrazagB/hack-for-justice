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
- **Accounts:** PostgreSQL 16, SQLAlchemy 2.0 (async), Argon2id, JWT sessions
- **Vector database:** Qdrant (self-hosted)
- **Embeddings:** BAAI/bge-m3 via HuggingFace Text Embeddings Inference (self-hosted)
- **OCR / vision:** an open-weight, Apache-2.0 multimodal model via Mistral's
  API, with a local Tesseract fallback
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

The LLM reasoning layer currently runs on vendor APIs for hackathon speed. That
layer has a credible self-hosting path too, because we deliberately use only
**open-weight, Apache-2.0 models** there — so "sovereign Sahilli" is an
incremental step, not a rewrite. See *Document OCR* below.

### Document OCR

Sahilli does **not** use Mistral's dedicated `mistral-ocr-*` product. That
product is a proprietary commercial API and is not open-weight; self-hosting it
requires a separate commercial licence. For a registry that must eventually run
this on its own infrastructure, "the weights are Apache-2.0" is a much stronger
guarantee than "you may self-host if you sign a contract".

Sahilli was originally specced around **Pixtral-12B** for that reason. Checking
Mistral's live model list rather than assuming turned out to matter: **Pixtral
has been retired from the API** — `pixtral-12b-2409` retired 2025-12-02 and
`pixtral-large-2411` retired 2026-02-27. The rationale carries over to its
open-weight successors:

| Model | Role |
|---|---|
| `ministral-14b-2512` (Ministral 3 14B, Apache-2.0) | default — verified working for OCR |
| `ministral-8b-2512` (Ministral 3 8B, Apache-2.0) | assistant text, and the lightest self-hosting target |

Both are open-weight and Apache-2.0, so the self-hosting path stays real.
Note that model *availability varies by account*: `mistral-large-2512`,
`mistral-small-latest` and `mistral-medium-latest` are not reachable on every
key, and an unavailable model answers `429 Rate limit exceeded` rather than a
404 — indistinguishable from a transient limit. Sahilli therefore asks the API
which models exist and picks the best available, for both OCR and chat.

Because model IDs churn, `ocr_service.py` queries the API for the models that
actually exist and picks the best available from a preference list. Override
with `VISION_MODEL` in `.env`.

**Tesseract fallback.** `pytesseract` provides a fully local, zero-cost, offline
path used when no API key is set, the API fails, or quota runs out. It is
markedly weaker — raw text only, no structured fields — so its results are
always marked `degraded=True` and should be treated as unverified. It exists so
a live demo never hard-fails on a conference network.

### What this repo expects to already be running

`docker-compose.yml` deliberately **does not define** Qdrant or an embedding
service. It expects them to already exist on the host, and the backend simply
points at them:

| Service | Image | Host port | Used for |
|---|---|---|---|
| Qdrant | `qdrant/qdrant` | **6333** (HTTP), 6334 (gRPC) | `rne_procedures` collection |
| Embeddings | `ghcr.io/huggingface/text-embeddings-inference` (`--model-id BAAI/bge-m3`) | **8090** | 1024-dim vectors |
| Postgres | `postgres:16-alpine` | **5432** | `sahilli` / `sahilli_test` databases |

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

4. Create the accounts databases (one-off):

   ```bash
   docker exec -i <postgres-container> psql -U <user> -d postgres \
     -c "CREATE DATABASE sahilli;" -c "CREATE DATABASE sahilli_test;"
   ```

   Tables are created automatically the first time the backend starts.

5. Seed the RAG grounding corpus into Qdrant (one-off):

   ```bash
   cd backend && uv run python ../scripts/seed_rag.py
   ```

6. Start the backend:

   ```bash
   cd backend
   uv run uvicorn app.main:app --reload
   ```

7. In another terminal, start the frontend:

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

## Accounts

Applicants sign up at `/signup` and sign in at `/login`. Sessions are JWTs in an
**httpOnly** cookie, so page JavaScript cannot read them and an XSS bug cannot
exfiltrate a session. Passwords are hashed with **Argon2id**.

**Officer accounts cannot be self-registered.** `POST /auth/signup` always
creates an applicant, because a self-grantable officer role would hand anyone
the review dashboard. Create one out of band:

```bash
cd backend && uv run python ../scripts/create_officer.py agent@rne.tn "Nom Agent"
```

| Endpoint | Purpose |
|---|---|
| `POST /auth/signup` | Register an applicant and start a session |
| `POST /auth/login` | Start a session |
| `GET /auth/me` | The signed-in user, or 401 |
| `POST /auth/logout` | Clear the session cookie |

> **`JWT_SECRET` must be replaced outside local development.** The default is in
> this repository, so anyone who has read it could mint a valid session. The
> backend logs a warning at startup while the default is in use.

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
