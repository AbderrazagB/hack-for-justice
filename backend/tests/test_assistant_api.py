"""Assistant tests.

The point of these is groundedness: the assistant must never invent procedural
facts, and must never contradict the rules engine.
"""

from __future__ import annotations

from unittest.mock import patch

from app.api.assistant import get_llm_client, get_retrieval_service
from app.main import app
from app.services.ocr_service import OCRResult, OCRService
from app.services.retrieval_service import RetrievedPassage
from tests.conftest import document_text

TXN = "RNE_MODIFICATION_ENTREPRISE"
ENDPOINT = f"/transactions/{TXN}/submissions"

DEADLINE_PASSAGE = RetrievedPassage(
    entry_id="rne-filing-deadline-one-month",
    topic="deadline",
    title_fr="Délai légal de dépôt — un mois",
    title_ar="الأجل القانوني للإيداع",
    text_fr="Les dépôts doivent être effectués dans un délai d'un mois...",
    text_ar="يجب إيداع المطالب في أجل شهر...",
    official_reference="Loi n° 52-2018 relative au Registre National des Entreprises",
    score=0.62,
    payload={},
)


class FakeRetrieval:
    def __init__(self, passages=None):
        self.passages = DEADLINE_PASSAGE if passages is None else passages
        self.queries = []

    def search(self, query, limit=3):
        self.queries.append(query)
        return [] if self.passages == [] else [DEADLINE_PASSAGE]


class FakeLLM:
    def __init__(self, answer="Il manque le procès-verbal."):
        self.answer = answer
        self.calls = []

    def generate(self, prompt, system=""):
        self.calls.append({"prompt": prompt, "system": system})
        return self.answer


def _fake_extract(self, content, filename="", document_type="general", force_local=False):
    return OCRResult(
        document_type=document_type,
        fields={},
        full_text=document_text(document_type),
        engine="test",
    )


def _create(client, png, doc_types):
    files = [("files", (f"{d}.png", png, "image/png")) for d in doc_types]
    with patch.object(OCRService, "extract", _fake_extract):
        response = client.post(
            ENDPOINT,
            files=files,
            data={"document_types": doc_types, "submitted_at": "2026-07-01"},
        )
    return response.json()["submission_id"]


def _wire(retrieval=None, llm=None):
    app.dependency_overrides[get_retrieval_service] = lambda: retrieval or FakeRetrieval()
    app.dependency_overrides[get_llm_client] = lambda: llm or FakeLLM()


# ------------------------------------------------------------------- basics

def test_explain_returns_answer_and_citations(client, png) -> None:
    llm = FakeLLM()
    _wire(llm=llm)
    submission_id = _create(client, png, ["id_new_representative"])

    body = client.post(
        "/assistant/explain", json={"submission_id": submission_id}
    ).json()

    assert body["answer"] == "Il manque le procès-verbal."
    assert body["grounded"] is True
    assert body["citations"][0]["official_reference"].startswith("Loi n° 52-2018")


def test_unknown_submission_is_404(client) -> None:
    _wire()
    assert client.post("/assistant/explain", json={"submission_id": "nope"}).status_code == 404


# -------------------------------------------------------------- groundedness

def test_prompt_carries_retrieved_context_and_verdict(client, png) -> None:
    llm = FakeLLM()
    _wire(llm=llm)
    submission_id = _create(client, png, ["id_new_representative"])
    client.post("/assistant/explain", json={"submission_id": submission_id})

    prompt = llm.calls[0]["prompt"]
    assert "RNE PROCEDURAL CONTEXT" in prompt
    assert "délai d'un mois" in prompt          # the retrieved passage
    assert "VALIDATION RESULT" in prompt
    assert "INCOMPLETE" in prompt                  # the rules-engine verdict


def test_system_prompt_forbids_inventing_procedural_facts(client, png) -> None:
    llm = FakeLLM()
    _wire(llm=llm)
    submission_id = _create(client, png, ["id_new_representative"])
    client.post("/assistant/explain", json={"submission_id": submission_id})

    system = llm.calls[0]["system"]
    assert "ONLY" in system
    assert "NEVER" in system
    assert "contradict the validation result" in system


def test_retrieval_query_is_built_from_the_actual_problems(client, png) -> None:
    """We retrieve on what went wrong, so the right passage comes back."""
    retrieval = FakeRetrieval()
    _wire(retrieval=retrieval)
    submission_id = _create(client, png, ["id_new_representative"])
    client.post("/assistant/explain", json={"submission_id": submission_id})

    query = retrieval.queries[0]
    assert "Procès-verbal" in query or "procès-verbal" in query.lower()


def test_explicit_question_overrides_the_derived_query(client, png) -> None:
    retrieval = FakeRetrieval()
    _wire(retrieval=retrieval)
    submission_id = _create(client, png, ["id_new_representative"])

    client.post(
        "/assistant/explain",
        json={"submission_id": submission_id, "question": "Quelle est la pénalité ?"},
    )
    assert retrieval.queries[0] == "Quelle est la pénalité ?"


# ----------------------------------------------------------------- fallbacks

def test_without_retrieval_it_reports_the_verdict_and_marks_ungrounded(client, png) -> None:
    """No corpus must not mean a freely improvising model."""
    _wire(retrieval=FakeRetrieval(passages=[]))
    submission_id = _create(client, png, ["id_new_representative"])

    body = client.post("/assistant/explain", json={"submission_id": submission_id}).json()
    assert body["grounded"] is False
    assert body["citations"] == []
    assert "INCOMPLETE" in body["answer"]


def test_llm_failure_degrades_to_the_deterministic_verdict(client, png) -> None:
    class Broken:
        def generate(self, prompt, system=""):
            raise RuntimeError("provider down")

    _wire(llm=Broken())
    submission_id = _create(client, png, ["id_new_representative"])

    response = client.post("/assistant/explain", json={"submission_id": submission_id})
    assert response.status_code == 200
    assert "INCOMPLETE" in response.json()["answer"]


# ------------------------------------------------------------------ language

def test_arabic_request_asks_for_arabic_and_arabic_citations(client, png) -> None:
    llm = FakeLLM(answer="ينقص محضر الجلسة العامة.")
    _wire(llm=llm)
    submission_id = _create(client, png, ["id_new_representative"])

    body = client.post(
        "/assistant/explain", json={"submission_id": submission_id, "lang": "ar"}
    ).json()

    assert body["lang"] == "ar"
    assert "Arabic" in llm.calls[0]["prompt"]
    assert body["citations"][0]["title"] == DEADLINE_PASSAGE.title_ar


def test_invalid_language_is_rejected(client, png) -> None:
    _wire()
    submission_id = _create(client, png, ["id_new_representative"])
    response = client.post(
        "/assistant/explain", json={"submission_id": submission_id, "lang": "de"}
    )
    assert response.status_code == 422


# ------------------------------------------------- assistant without a filing

def test_explain_answers_without_a_submission(client) -> None:
    """The floating assistant is reachable before anything is uploaded."""
    llm = FakeLLM("Le dépôt se fait en ligne.")
    _wire(llm=llm)

    response = client.post(
        "/assistant/explain", json={"question": "Quelles pièces dois-je fournir ?"}
    )
    assert response.status_code == 200

    body = response.json()
    assert body["answer"] == "Le dépôt se fait en ligne."
    assert body["grounded"] is True
    assert body["submission_id"] is None


def test_prompt_without_a_submission_forbids_claims_about_documents(client) -> None:
    llm = FakeLLM()
    _wire(llm=llm)
    client.post("/assistant/explain", json={"question": "Quel est le délai ?"})

    prompt = llm.calls[0]["prompt"]
    # No filing was checked, so the model must be told there is no verdict
    # rather than being handed an empty one it could read as "all clear".
    assert "No filing has been checked yet" in prompt
    assert "do not claim anything about the user's documents" in prompt
    assert "délai d'un mois" in prompt


def test_question_without_a_submission_drives_retrieval(client) -> None:
    retrieval = FakeRetrieval()
    _wire(retrieval=retrieval)
    client.post("/assistant/explain", json={"question": "Quelle est la pénalité ?"})

    assert retrieval.queries == ["Quelle est la pénalité ?"]


def test_empty_question_without_a_submission_still_retrieves(client) -> None:
    retrieval = FakeRetrieval()
    _wire(retrieval=retrieval)
    body = client.post("/assistant/explain", json={}).json()

    assert retrieval.queries and retrieval.queries[0]
    assert body["grounded"] is True


def test_ungrounded_without_a_submission_declines_rather_than_guessing(client) -> None:
    """With neither a verdict nor retrieved text, there is nothing honest to say."""
    _wire(retrieval=FakeRetrieval(passages=[]))

    body = client.post(
        "/assistant/explain", json={"question": "Quel est le délai ?"}
    ).json()

    assert body["grounded"] is False
    assert "n'ont pas pu être consultés" in body["answer"]
    # It must not fall back to a verdict block: there is no filing.
    assert "Statut:" not in body["answer"]


def test_ungrounded_with_a_submission_still_reports_the_verdict(client, png) -> None:
    _wire(retrieval=FakeRetrieval(passages=[]))
    submission_id = _create(client, png, ["id_new_representative"])

    body = client.post(
        "/assistant/explain", json={"submission_id": submission_id}
    ).json()

    assert body["grounded"] is False
    assert "Statut:" in body["answer"]
