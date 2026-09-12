#!/usr/bin/env bash
# Generate the synthetic demo dataset and push it through the running API, so
# the officer dashboard has a realistic queue before a demo starts.
#
#   ./scripts/seed_demo_data.sh [API_URL]
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_URL="${1:-http://localhost:8000}"
DEMO_DIR="$PROJECT_DIR/data/demo"

echo "Generating synthetic demo documents..."
(cd "$PROJECT_DIR/backend" && uv run python ../data/generate_sample_data.py --out "$DEMO_DIR")

if ! curl -sf "$API_URL/health" >/dev/null; then
  echo
  echo "Documents are in $DEMO_DIR, but the API at $API_URL is not reachable,"
  echo "so nothing was submitted. Start it with:"
  echo "  cd backend && uv run uvicorn app.main:app --reload"
  exit 1
fi

echo
echo "Submitting cases to $API_URL..."
python3 - "$API_URL" "$DEMO_DIR" <<'PY'
import json, sys, urllib.request, uuid
from pathlib import Path

api_url, demo_dir = sys.argv[1], Path(sys.argv[2])
manifest = json.loads((demo_dir / "manifest.json").read_text(encoding="utf-8"))

for case in manifest["cases"]:
    boundary = uuid.uuid4().hex
    parts = []
    for doc_type, path in case["documents"].items():
        content = Path(path).read_bytes()
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="files"; '
            f'filename="{doc_type}.png"\r\nContent-Type: image/png\r\n\r\n'.encode()
            + content + b"\r\n"
        )
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; '
            f'name="document_types"\r\n\r\n{doc_type}\r\n'.encode()
        )
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; '
        f'name="submitted_at"\r\n\r\n{case["submitted_at"]}\r\n'.encode()
    )
    parts.append(f"--{boundary}--\r\n".encode())

    request = urllib.request.Request(
        f"{api_url}/transactions/RNE_MODIFICATION_ENTREPRISE/submissions",
        data=b"".join(parts),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(request) as response:
        body = json.load(response)
    print(f"  {case['case_id']}  {body['completeness']['status']:<12} "
          f"flags={body['flag_summary']['total']}  {case['label']}")
PY

echo
echo "Done. Open the officer dashboard at http://localhost:3000/admin"
