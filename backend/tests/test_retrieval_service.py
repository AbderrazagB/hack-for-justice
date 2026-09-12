"""Retrieval layer tests.

Unit tests run against an in-memory Qdrant with a deterministic fake embedder,
so they need no containers. The integration test at the bottom exercises the
real external Qdrant + BGE-M3 and skips cleanly when they are not running.
"""

from __future__ import annotations

import hashlib

import pytest
from qdrant_client import QdrantClient

from app.core.vector_store import VectorStore
from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import (
    RetrievalService,
    embeddable_text,
    load_seed_entries,
)

DIM = 32


class FakeEmbedder:
    """Deterministic hash-based embedder. Same text -> same vector."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_one(self, text: str) -> list[float]:
        return self._vector(text)

    @staticmethod
    def _vector(text: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        return [digest[i % len(digest)] / 255.0 for i in range(DIM)]


@pytest.fixture
def service() -> RetrievalService:
    # Force a private in-memory Qdrant. QDRANT_URL normally points at the shared
    # host container, and unit tests must never write into it.
    store = VectorStore("test_rne_procedures")
    store.client = QdrantClient(location=":memory:")
    svc = RetrievalService(vector_store=store, embedding_service=FakeEmbedder())
    svc.vector_store.init_collection(vector_size=DIM)
    return svc


# ------------------------------------------------------------------ corpus

def test_seed_corpus_has_the_four_curated_entries() -> None:
    topics = {entry["topic"] for entry in load_seed_entries()}
    assert topics == {"required_documents", "deadline", "penalty", "submission_channel"}


def test_modification_deadline_entry_records_one_month() -> None:
    """Article 26 says "un mois", not thirty days."""
    entry = next(
        e for e in load_seed_entries() if e["id"] == "rne-filing-deadline-30-days"
    )
    assert entry["deadline_months"] == 1
    assert "deadline_days" not in entry
    assert "article 26" in entry["official_reference"]


def test_required_documents_match_the_rne_m_005_checklist() -> None:
    entry = next(e for e in load_seed_entries() if e["topic"] == "required_documents")
    assert entry["official_reference"] == "RNE-M-005"
    assert entry["required_documents"] == [
        "id_new_representative",
        "company_statutes",
        "rne_extract",
        "tax_registration_card",
        "general_assembly_pv",
    ]


def test_digital_only_entry_records_the_july_2026_cutover() -> None:
    entry = next(e for e in load_seed_entries() if e["topic"] == "submission_channel")
    assert entry["effective_date"] == "2026-07-01"


def test_every_entry_is_bilingual_and_cited() -> None:
    for entry in load_seed_entries():
        assert entry["text_fr"] and entry["text_ar"], entry["id"]
        assert entry["official_reference"], entry["id"]


def test_embeddable_text_includes_both_languages() -> None:
    entry = load_seed_entries()[0]
    text = embeddable_text(entry)
    assert entry["text_fr"] in text
    assert entry["text_ar"] in text


# --------------------------------------------------------------- retrieval

def test_index_then_retrieve_exact_entry(service: RetrievalService) -> None:
    entries = load_seed_entries()
    assert service.index_entries(entries) == len(entries)

    deadline = next(e for e in entries if e["topic"] == "deadline")
    hits = service.search(embeddable_text(deadline), limit=1)
    assert hits[0].entry_id == deadline["id"]
    assert hits[0].citation() == deadline["official_reference"]


def test_reindexing_is_idempotent(service: RetrievalService) -> None:
    entries = load_seed_entries()
    service.index_entries(entries)
    service.index_entries(entries)
    assert service.vector_store.count() == len(entries)


def test_empty_query_returns_nothing(service: RetrievalService) -> None:
    service.index_entries(load_seed_entries())
    assert service.search("   ") == []


def test_search_swallows_backend_failure(service: RetrievalService) -> None:
    """Retrieval must degrade to empty, never raise into the API layer."""
    class Broken:
        def embed_one(self, text: str): raise RuntimeError("embedding server down")
        def embed(self, texts): raise RuntimeError("embedding server down")

    service.embedding_service = Broken()
    assert service.search("délai") == []


def test_context_for_renders_citations(service: RetrievalService) -> None:
    entries = load_seed_entries()
    service.index_entries(entries)
    deadline = next(
        e for e in entries if e["id"] == "rne-filing-deadline-30-days"
    )

    context = service.context_for(embeddable_text(deadline), limit=1, lang="fr")
    assert deadline["official_reference"] in context
    assert "un mois" in context

    arabic = service.context_for(embeddable_text(deadline), limit=1, lang="ar")
    assert deadline["text_ar"] in arabic


# ------------------------------------------------------------- integration

@pytest.mark.integration
def test_live_containers_return_the_deadline_entry() -> None:
    """The milestone check: a real query hits the real stack."""
    embedder = EmbeddingService()
    if not embedder.health():
        pytest.skip("external BGE-M3 container not running")

    live = RetrievalService(embedding_service=embedder)
    if not live.is_ready():
        pytest.skip("rne_procedures collection not seeded; run scripts/seed_rag.py")

    for query in [
        "Quel est le délai légal pour déposer une modification ?",
        "ما هو الأجل القانوني للإيداع؟",
    ]:
        hits = live.search(query, limit=1)
        assert hits, query
        assert hits[0].topic == "deadline", query
        assert "52-2018" in hits[0].official_reference


# ------------------------------------- financial statements corpus entries

def test_corpus_covers_both_workflows() -> None:
    types = {e.get("transaction_type") for e in load_seed_entries()}
    assert types == {"RNE_MODIFICATION_ENTREPRISE", "RNE_FINANCIAL_STATEMENTS"}


def test_financial_statements_deadline_entry_records_seven_months() -> None:
    entry = next(
        e
        for e in load_seed_entries()
        if e["id"] == "rne-financial-statements-deadline-7-months"
    )
    assert entry["deadline_months"] == 7
    assert "52-2018" in entry["official_reference"]


def test_financial_statements_penalty_entry_records_both_rates() -> None:
    entry = next(
        e for e in load_seed_entries() if e["id"] == "rne-financial-statements-penalty"
    )
    assert entry["penalty_tnd_per_month_legal_entity"] == 25
    assert entry["penalty_tnd_per_month_individual"] == 10


def test_financial_statements_documents_match_the_rules_engine() -> None:
    """The corpus and the rules engine must not drift apart."""
    from app.services.rules_engine import TRANSACTION_RULES

    entry = next(
        e
        for e in load_seed_entries()
        if e["id"] == "rne-financial-statements-required-documents"
    )
    assert (
        entry["required_documents"]
        == TRANSACTION_RULES["RNE_FINANCIAL_STATEMENTS"]["required_documents"]
    )


def test_each_workflow_retrieves_its_own_deadline(service: RetrievalService) -> None:
    """Two deadlines in one collection must not shadow each other."""
    entries = load_seed_entries()
    service.index_entries(entries)

    for entry_id in (
        "rne-filing-deadline-30-days",
        "rne-financial-statements-deadline-7-months",
    ):
        entry = next(e for e in entries if e["id"] == entry_id)
        hits = service.search(embeddable_text(entry), limit=1)
        assert hits[0].entry_id == entry_id


@pytest.mark.integration
def test_live_stack_separates_the_two_deadlines() -> None:
    embedder = EmbeddingService()
    if not embedder.health():
        pytest.skip("external BGE-M3 container not running")

    live = RetrievalService(embedding_service=embedder)
    if not live.is_ready():
        pytest.skip("rne_procedures collection not seeded; run scripts/seed_rag.py")

    probes = {
        "Quel est le délai pour déposer les états financiers annuels ?":
            "rne-financial-statements-deadline-7-months",
        "ما هو أجل إيداع القوائم المالية؟":
            "rne-financial-statements-deadline-7-months",
        "Quel est le délai légal pour déposer une modification d'entreprise ?":
            "rne-filing-deadline-30-days",
    }
    for query, expected in probes.items():
        hits = live.search(query, limit=1)
        assert hits and hits[0].entry_id == expected, query
