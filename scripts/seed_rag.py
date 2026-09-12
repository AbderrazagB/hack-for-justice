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

    # Smoke tests: one canonical query per workflow must retrieve that
    # workflow's own entry, not the other's. With both corpora in one
    # collection, a query about one deadline must not surface the other.
    probes = [
        (
            "Quel est le délai légal pour déposer une modification d'entreprise ?",
            "rne-filing-deadline-30-days",
        ),
        (
            "Quel est le délai pour déposer les états financiers annuels ?",
            "rne-financial-statements-deadline-7-months",
        ),
        (
            "Quelles pièces pour le dépôt des états financiers ?",
            "rne-financial-statements-required-documents",
        ),
    ]

    failures = 0
    print()
    for probe, expected in probes:
        results = service.search(probe, limit=2)
        top = results[0] if results else None
        ok = top is not None and top.entry_id == expected
        failures += 0 if ok else 1
        print(f"{'OK  ' if ok else 'MISS'} {probe}")
        for rank, passage in enumerate(results, start=1):
            print(f"       {rank}. [{passage.score:.4f}] {passage.entry_id}")

    if failures:
        print(f"\nWARNING: {failures} probe(s) did not retrieve the expected entry.", file=sys.stderr)
        return 1

    print("\nSeeding complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
