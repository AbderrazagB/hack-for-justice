"""The officer's brief, and the applicant's view of their own dossiers.

Two sides of the same gap: the officer had to assemble the picture by reading
five documents, and the applicant could not see a filing again once they had
closed the tab.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

from app.api.auth import current_user
from app.api.brief import at_a_glance, get_llm_client, get_retrieval_service
from app.main import app
from app.models.user import User, UserRole
from app.services.ocr_service import OCRResult, OCRService
from app.services.retrieval_service import RetrievedPassage
from tests.conftest import document_text

TXN = "RNE_MODIFICATION_ENTREPRISE"
ENDPOINT = f"/transactions/{TXN}/submissions"

PASSAGE = RetrievedPassage(
    entry_id="rne-checklist",
    topic="required_documents",
    title_fr="Pièces requises",
    title_ar="الوثائق المطلوبة",
    text_fr="Les pièces requises sont ...",
    text_ar="الوثائق المطلوبة هي ...",
    official_reference="RNE-M-005",
    score=0.6,
    payload={},
)


class FakeRetrieval:
    def __init__(self, passages=None):
        self.passages = [PASSAGE] if passages is None else passages

    def search(self, query, limit=3):
        return self.passages


class FakeLLM:
    def __init__(self, answer="Le CIN diverge entre la carte et le procès-verbal."):
        self.answer = answer
        self.calls = []

    def generate(self, prompt, system=""):
        self.calls.append({"prompt": prompt, "system": system})
        return self.answer


def _fake_extract(self, content, filename="", document_type="general", force_local=False):
    fields = {
        "id_new_representative": {"id_number": "12345678", "person_name": "Amine Ben Salah"},
        "general_assembly_pv": {"id_number": "87654321", "person_name": "Amine Ben Salah"},
    }.get(document_type, {})
    return OCRResult(
        document_type=document_type,
        fields=dict(fields),
        full_text=document_text(document_type),
        engine="test",
    )


def _create(client, png, doc_types=("id_new_representative", "general_assembly_pv")):
    files = [("files", (f"{d}.png", png, "image/png")) for d in doc_types]
    with patch.object(OCRService, "extract", _fake_extract):
        return client.post(
            ENDPOINT, files=files, data={"document_types": list(doc_types)}
        ).json()["submission_id"]


def _wire(retrieval=None, llm=None):
    app.dependency_overrides[get_retrieval_service] = lambda: retrieval or FakeRetrieval()
    app.dependency_overrides[get_llm_client] = lambda: llm or FakeLLM()


# ------------------------------------------------------------- at a glance

def test_at_a_glance_counts_come_from_the_verdict() -> None:
    payload = {
        "status": "SUBMITTED",
        "completeness": {
            "status": "NEEDS_REVIEW",
            "checks": [{"outcome": "PASS"}, {"outcome": "FAIL"}, {"outcome": "PASS"}],
            "present_documents": ["a", "b"],
            "missing_documents": [{"key": "rne_extract", "label_fr": "Extrait RNE"}],
        },
        "flags": [
            {
                "severity": "ERROR",
                "documents": [{"key": "general_assembly_pv", "label_fr": "PV"}],
            },
            {"severity": "WARNING", "documents": []},
        ],
        "reviews": [],
    }
    glance = at_a_glance(payload)

    assert glance["errors"] == 1
    assert glance["warnings"] == 1
    assert glance["checks_passed"] == 2
    assert glance["checks_total"] == 3
    assert glance["blocking_documents"] == [{"key": "general_assembly_pv", "label_fr": "PV"}]
    assert glance["documents_missing"][0]["label_fr"] == "Extrait RNE"


def test_a_document_blocking_twice_is_listed_once() -> None:
    payload = {
        "completeness": {},
        "flags": [
            {"severity": "ERROR", "documents": [{"key": "pv", "label_fr": "PV"}]},
            {"severity": "ERROR", "documents": [{"key": "pv", "label_fr": "PV"}]},
        ],
    }
    assert len(at_a_glance(payload)["blocking_documents"]) == 1


# ------------------------------------------------------------------- brief

def test_brief_is_officer_only(client, png) -> None:
    """It summarises another applicant's dossier."""
    _wire()
    submission_id = _create(client, png)
    assert client.get(f"/submissions/{submission_id}/brief").status_code == 403


def test_brief_carries_the_facts_and_a_summary(officer_client, png) -> None:
    llm = FakeLLM()
    _wire(llm=llm)
    submission_id = _create(officer_client, png)

    body = officer_client.get(f"/submissions/{submission_id}/brief").json()
    assert body["grounded"] is True
    assert body["summary"] == "Le CIN diverge entre la carte et le procès-verbal."
    assert body["at_a_glance"]["errors"] >= 1


def test_the_brief_must_not_recommend_a_decision(officer_client, png) -> None:
    """The officer decides. The brief saves reading time, nothing more."""
    llm = FakeLLM()
    _wire(llm=llm)
    submission_id = _create(officer_client, png)
    officer_client.get(f"/submissions/{submission_id}/brief")

    system = llm.calls[0]["system"]
    assert "Do NOT recommend a decision" in system
    assert "The officer decides" in system


def test_brief_without_retrieval_still_states_the_verdict(officer_client, png) -> None:
    _wire(retrieval=FakeRetrieval(passages=[]))
    submission_id = _create(officer_client, png)

    body = officer_client.get(f"/submissions/{submission_id}/brief").json()
    assert body["grounded"] is False
    assert body["summary"]


def test_brief_on_an_unknown_submission_is_404(officer_client) -> None:
    _wire()
    assert officer_client.get("/submissions/nope/brief").status_code == 404


# ---------------------------------------------------- the applicant's list

def test_mine_lists_only_your_own_dossiers(client, png) -> None:
    submission_id = _create(client, png)
    body = client.get("/submissions/mine").json()

    assert body["count"] == 1
    assert body["submissions"][0]["id"] == submission_id


def test_mine_requires_a_session(anon_client) -> None:
    assert anon_client.get("/submissions/mine").status_code == 401


# ------------------------------------------------------ submit for review

def test_submitting_moves_the_dossier_into_review(client, png) -> None:
    submission_id = _create(client, png)
    response = client.post(f"/submissions/{submission_id}/submit")

    assert response.status_code == 200
    assert response.json()["status"] == "UNDER_INSTITUTIONAL_REVIEW"
    assert client.get(f"/submissions/{submission_id}").json()["status"] == (
        "UNDER_INSTITUTIONAL_REVIEW"
    )


def test_a_flagged_dossier_may_still_be_submitted(client, png) -> None:
    """Sahilli pre-validates; it does not stand between an applicant and the
    registry. An applicant may disagree with a warning."""
    submission_id = _create(client, png)
    detail = client.get(f"/submissions/{submission_id}").json()
    assert detail["flags"], "fixture should raise at least one flag"

    assert client.post(f"/submissions/{submission_id}/submit").status_code == 200


def test_submitting_someone_elses_dossier_is_403(client, png) -> None:
    submission_id = _create(client, png)

    # Two clients in one test fight over the dependency overrides, so the
    # stranger is installed directly.
    stranger = User(
        id=uuid.uuid4(),
        email="stranger@example.tn",
        password_hash="x",
        full_name="Stranger",
        role=UserRole.APPLICANT.value,
    )
    app.dependency_overrides[current_user] = lambda: stranger

    assert client.post(f"/submissions/{submission_id}/submit").status_code == 403


def test_submitting_requires_a_session(anon_client) -> None:
    assert anon_client.post("/submissions/x/submit").status_code == 401


def test_a_decided_dossier_cannot_be_resubmitted(officer_client, png) -> None:
    submission_id = _create(officer_client, png)
    officer_client.post(f"/submissions/{submission_id}/review", json={"action": "approve"})

    response = officer_client.post(f"/submissions/{submission_id}/submit")
    assert response.status_code == 409


def test_the_brief_retrieves_on_this_procedure_not_a_generic_string(
    officer_client, png
) -> None:
    """A clean Modification Entreprise once retrieved the annual-statements
    entry, and the brief described états financiers on a manager change."""

    class Recording(FakeRetrieval):
        def __init__(self):
            super().__init__()
            self.queries: list[str] = []

        def search(self, query, limit=3):
            self.queries.append(query)
            return self.passages

    retrieval = Recording()
    _wire(retrieval=retrieval)
    submission_id = _create(officer_client, png)
    officer_client.get(f"/submissions/{submission_id}/brief")

    assert "Modification Entreprise" in retrieval.queries[0]


def test_the_brief_is_told_to_stay_inside_this_procedure(officer_client, png) -> None:
    llm = FakeLLM()
    _wire(llm=llm)
    submission_id = _create(officer_client, png)
    officer_client.get(f"/submissions/{submission_id}/brief")

    assert "Describe ONLY that procedure" in llm.calls[0]["system"]
