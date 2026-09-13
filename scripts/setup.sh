#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ ! -f "$PROJECT_DIR/.env" ] && [ -f "$PROJECT_DIR/.env.example" ]; then
  cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
  echo "Created .env from .env.example -- add your MISTRAL_API_KEY before starting."
fi

echo "Syncing backend Python dependencies with uv..."
(cd "$PROJECT_DIR/backend" && uv sync)

echo "Installing frontend Node.js dependencies with npm..."
(cd "$PROJECT_DIR/frontend" && npm install)

# The shipped JWT_SECRET is in the repository, so anyone who has read it could
# mint a valid session. A fresh clone gets its own before it ever serves a
# request; an operator who set their own is left alone.
DEFAULT_SECRET="sahilli-local-development-secret-do-not-use-in-production"
ENV_FILE="$PROJECT_DIR/.env"

if [ -f "$ENV_FILE" ] && grep -q "^JWT_SECRET=$DEFAULT_SECRET$" "$ENV_FILE"; then
  SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
  # A literal replacement, so a secret containing / or & cannot break sed.
  python3 - "$ENV_FILE" "$DEFAULT_SECRET" "$SECRET" <<'PYEOF'
import sys
path, old, new = sys.argv[1:4]
with open(path, encoding="utf-8") as handle:
    text = handle.read()
with open(path, "w", encoding="utf-8") as handle:
    handle.write(text.replace(f"JWT_SECRET={old}", f"JWT_SECRET={new}", 1))
PYEOF
  echo "Generated a unique JWT_SECRET in .env (the shipped default was still in place)."
fi

echo
echo "Setup complete. Next:"
echo "  docker compose --profile infra up -d   # Postgres, Qdrant, embeddings, MinIO"
echo "  cd backend && uv run python ../scripts/seed_rag.py"
echo "  cd backend && uv run uvicorn app.main:app --reload"
echo
echo "Already running those services? Point .env at them and skip the compose step."

