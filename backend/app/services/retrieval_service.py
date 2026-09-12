"""RAG retrieval over RNE procedural text.

Grounds Sahilli's assistant in a small, hand-curated corpus of real RNE
procedural text (data/seed/rne_procedures.json) rather than the model's own
recollection of Tunisian registry law. Every answer the assistant gives about
deadlines, penalties or required documents must trace back to a retrieved
passage -- if it is not in the corpus, the assistant says it does not know.

Vectors come from the external BGE-M3 container and land in the external
Qdrant collection "rne_procedures". See README > Local AI Infrastructure.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from qdrant_client import models

from app.core.vector_store import VectorStore
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

COLLECTION_NAME = "rne_procedures"

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SEED_PATH = PROJECT_ROOT / "data" / "seed" / "rne_procedures.json"

# Deterministic point IDs so re-running the seeder updates rows in place rather
# than duplicating the corpus. Qdrant needs a UUID or int, and our entry ids are
# human-readable slugs, so derive a stable UUID5 from each slug.
_ID_NAMESPACE = uuid.UUID("6f9619ff-8b86-d011-b42d-00c04fc964ff")


def _point_id(entry_id: str) -> str:
    return str(uuid.uuid5(_ID_NAMESPACE, entry_id))


@dataclass
class RetrievedPassage:
    """One grounding passage, with the citation the assistant must show."""

    entry_id: str
    topic: str
    title_fr: str
    title_ar: str
    text_fr: str
    text_ar: str
    official_reference: str
    score: float
    payload: dict[str, Any]

    def citation(self) -> str:
        return self.official_reference

    def as_context(self, lang: str = "fr") -> str:
        """Render for injection into an LLM prompt, citation attached."""
        title = self.title_ar if lang == "ar" else self.title_fr
        body = self.text_ar if lang == "ar" else self.text_fr
        return f"[{self.official_reference}] {title}\n{body}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "topic": self.topic,
            "title_fr": self.title_fr,
            "title_ar": self.title_ar,
            "text_fr": self.text_fr,
            "text_ar": self.text_ar,
            "official_reference": self.official_reference,
            "score": self.score,
        }


def load_seed_entries(path: Path | None = None) -> list[dict[str, Any]]:
    """Read the curated corpus from disk."""
    source = path or SEED_PATH
    with source.open(encoding="utf-8") as handle:
        return json.load(handle)["entries"]


def embeddable_text(entry: dict[str, Any]) -> str:
    """Build the string that gets embedded for one corpus entry.

    Both language variants go into a single vector. BGE-M3 is explicitly
    multilingual, so a French query and an Arabic query both land near the same
    point -- which is what we need for a bilingual FR/AR interface.
    """
    parts = [
        entry.get("title_fr", ""),
        entry.get("title_ar", ""),
        entry.get("text_fr", ""),
        entry.get("text_ar", ""),
        entry.get("official_reference", ""),
    ]
    return "\n".join(part for part in parts if part)


class RetrievalService:
    """Embed-and-search over the RNE procedural corpus."""

    def __init__(
        self,
        vector_store: VectorStore | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self.vector_store = vector_store or VectorStore(COLLECTION_NAME)
        self.embedding_service = embedding_service or EmbeddingService()

    # ------------------------------------------------------------- ingestion

    def index_entries(self, entries: list[dict[str, Any]]) -> int:
        """Embed and upsert corpus entries. Idempotent across runs."""
        if not entries:
            return 0

        self.vector_store.init_collection()
        vectors = self.embedding_service.embed(
            [embeddable_text(entry) for entry in entries]
        )
        self.vector_store.upsert(
            [
                models.PointStruct(
                    id=_point_id(entry["id"]),
                    vector=vector,
                    payload=entry,
                )
                for entry, vector in zip(entries, vectors, strict=True)
            ]
        )
        return len(entries)

    def seed_from_disk(self, path: Path | None = None) -> int:
        return self.index_entries(load_seed_entries(path))

    # ------------------------------------------------------------- retrieval

    def search(self, query: str, limit: int = 3) -> list[RetrievedPassage]:
        """Return the passages most relevant to a natural-language query."""
        if not query.strip():
            return []

        try:
            vector = self.embedding_service.embed_one(query)
            hits = self.vector_store.search(vector, limit=limit)
        except Exception as exc:  # noqa: BLE001 - retrieval must never 500 the API
            logger.warning("Retrieval failed for %r: %s", query, exc)
            return []

        passages: list[RetrievedPassage] = []
        for hit in hits:
            payload = hit.payload or {}
            passages.append(
                RetrievedPassage(
                    entry_id=payload.get("id", ""),
                    topic=payload.get("topic", ""),
                    title_fr=payload.get("title_fr", ""),
                    title_ar=payload.get("title_ar", ""),
                    text_fr=payload.get("text_fr", ""),
                    text_ar=payload.get("text_ar", ""),
                    official_reference=payload.get("official_reference", ""),
                    score=float(hit.score),
                    payload=payload,
                )
            )
        return passages

    def context_for(self, query: str, limit: int = 3, lang: str = "fr") -> str:
        """Concatenated, citation-tagged context block for an LLM prompt."""
        passages = self.search(query, limit=limit)
        return "\n\n".join(passage.as_context(lang) for passage in passages)

    def is_ready(self) -> bool:
        """True when the collection exists and holds the corpus."""
        try:
            return self.vector_store.count() > 0
        except Exception:  # noqa: BLE001
            return False
