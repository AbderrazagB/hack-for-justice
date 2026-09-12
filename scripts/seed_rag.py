#!/usr/bin/env python
"""Seed the RNE procedural corpus into the external Qdrant container.

Idempotent: point IDs are derived from each entry's slug, so re-running updates
rows in place instead of duplicating them.

    cd backend && uv run python ../scripts/seed_rag.py
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from app.core.config import settings
from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import (
    COLLECTION_NAME,
    RetrievalService,
    load_seed_entries,
)


def main() -> int:
    print(f"Qdrant      : {settings.qdrant_url or '(in-memory)'}")
    print(f"Embeddings  : {settings.embedding_service_url}")

    embedder = EmbeddingService()
    if not embedder.health():
        print(
            f"\nERROR: embedding service unreachable at {settings.embedding_service_url}.\n"
            "Start the BGE-M3 container -- see README > Local AI Infrastructure.",
            file=sys.stderr,
        )
        return 1

    entries = load_seed_entries()
    print(f"Loaded {len(entries)} curated entries from data/seed/rne_procedures.json")

    service = RetrievalService(embedding_service=embedder)
    count = service.index_entries(entries)
    print(f"Indexed {count} entries into collection '{COLLECTION_NAME}'")

    # Smoke test: the canonical query for the legal deadline must come back first.
    probe = "Quel est le délai légal pour déposer une modification ?"
    results = service.search(probe, limit=2)
    print(f"\nSmoke test: {probe}")
    for rank, passage in enumerate(results, start=1):
        print(f"  {rank}. [{passage.score:.4f}] {passage.entry_id} — {passage.title_fr}")

    if not results or results[0].topic != "deadline":
        print("\nWARNING: expected the 30-day deadline entry to rank first.", file=sys.stderr)
        return 1

    print("\nSeeding complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
