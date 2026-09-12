#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Syncing backend Python dependencies with uv..."
(cd "$PROJECT_DIR/backend" && uv sync)

echo "Installing frontend Node.js dependencies with npm..."
(cd "$PROJECT_DIR/frontend" && npm install)

echo "Setup complete."

