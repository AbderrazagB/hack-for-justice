# [Project Name] — Hack4Justice

> One-line problem statement: describe the justice challenge this project addresses.

## Tech stack

- **Backend:** FastAPI, Python 3.11+, and uv
- **Frontend:** Next.js (App Router), TypeScript, and Tailwind CSS
- **Vector database:** Qdrant
- **AI providers:** Mistral and Google Gemini

## Prerequisites

- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/) installed
- Node.js 20.9 or newer (required by the current Next.js release)
- Docker and Docker Compose (optional)

## Setup

1. Clone the repository and enter it:

   ```bash
   git clone <repository-url>
   cd hack4justice-project
   ```

2. Create your local environment file and add API keys:

   ```bash
   cp .env.example .env
   ```

3. Install backend and frontend dependencies:

   ```bash
   ./scripts/setup.sh
   ```

4. Start the backend:

   ```bash
   cd backend
   uv run uvicorn app.main:app --reload
   ```

5. In another terminal, start the frontend:

   ```bash
   cd frontend
   npm run dev
   ```

Open http://localhost:3000. The FastAPI docs are at http://localhost:8000/docs.

To run the complete stack with Docker instead:

```bash
docker-compose up --build
```

## Project structure

```text
backend/    FastAPI application, integrations, services, and tests
frontend/   Next.js web application and shared UI code
data/       Raw, processed, schema, and generated demo data
prompts/    Version-controlled LLM prompts and examples
notebooks/  Exploratory notebooks
docs/       Architecture notes and demo guide
scripts/    Local setup and data-seeding helpers
```

## Team

- [Name] — [Role]
