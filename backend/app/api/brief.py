"""The officer's thirty-second read of a dossier.

An officer opening a filing today gets the anomalies, five documents and their
extracted fields, and has to assemble the picture themselves. This assembles it
once: what is blocking, what merely needs a look, which document each finding sits
in, and how long the dossier has been waiting.

The counts and the pointers are computed from the stored verdict -- they are
the rules engine's own findings, rearranged. Only the closing paragraph is
written by a model, and it is given the verdict and the retrieved RNE text and
nothing else. It never decides: the decision buttons are three clicks away and
they belong to the officer.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.auth import current_officer
from app.core.llm_client import LLMClient
from app.core.rate_limit import ASSISTANT_LIMIT, enforce
from app.models.submission import SubmissionStore, get_store
from app.models.user import User
from app.services.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["brief"])

SYSTEM_PROMPT = """You are briefing an officer of Tunisia's national business \
registry (RNE) who is about to decide on a filing.

Absolute rules:
- Use ONLY the VALIDATION RESULT and the RNE PROCEDURAL CONTEXT provided.
- NEVER state a deadline, penalty, fee or document requirement that is not in \
the provided context.
- NEVER contradict the validation result. It is authoritative.
- Do NOT recommend a decision. Do not write "approve", "reject" or "request a \
correction". The officer decides; your job is to save them reading time.
- Do NOT invent an article number, a URL, an office, a fee or a procedural step.
- The VALIDATION RESULT names the procedure. Describe ONLY that procedure. Retrieved context may mention other RNE procedures; requirements belonging to them (annual financial statements, auditor reports, shareholder lists on a manager change, and so on) must not appear in your brief.
- Restate every deadline and amount in exactly the units the context uses.

Write at most 70 words, in French, as one short paragraph. Say what is wrong, \
which document it sits in, and what the applicant would have to change. If \
nothing is wrong, say the file is consistent and what was checked."""


class BriefResponse(BaseModel):
    submission_id: str
    at_a_glance: dict[str, Any]
    summary: str
    grounded: bool = Field(description="False when no RNE text could be retrieved.")


def get_retrieval_service() -> RetrievalService:
    return RetrievalService()


def get_llm_client() -> LLMClient:
    return LLMClient()


@router.get("/submissions/{submission_id}/brief", response_model=BriefResponse)
def brief(
    submission_id: str,
    http_request: Request,
    store: SubmissionStore = Depends(get_store),
    retrieval: RetrievalService = Depends(get_retrieval_service),
    llm: Annotated[LLMClient, Depends(get_llm_client)] = None,
    officer: User = Depends(current_officer),
) -> BriefResponse:
    enforce(http_request, "brief", ASSISTANT_LIMIT)

    submission = store.get(submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail=f"No submission '{submission_id}'")

    payload = submission.to_dict()
    glance = at_a_glance(payload)

    verdict = _verdict_text(payload)
    passages = retrieval.search(_query(payload), limit=2)

    if not passages:
        return BriefResponse(
            submission_id=submission_id,
            at_a_glance=glance,
            summary=_deterministic_summary(glance),
            grounded=False,
        )

    prompt = (
        "VALIDATION RESULT (authoritative, produced by deterministic rules):\n"
        f"{verdict}\n\n"
        "RNE PROCEDURAL CONTEXT (the only permitted source of procedural facts):\n"
        + "\n\n".join(p.as_context("fr") for p in passages)
        + "\n\nBrief the officer."
    )

    try:
        summary = (llm or LLMClient()).generate(prompt, system=SYSTEM_PROMPT).strip()
    except Exception as exc:  # noqa: BLE001 - a brief is a convenience, not a gate
        logger.warning("Brief generation failed: %s", exc)
        return BriefResponse(
            submission_id=submission_id,
            at_a_glance=glance,
            summary=_deterministic_summary(glance),
            grounded=False,
        )

    return BriefResponse(
        submission_id=submission_id,
        at_a_glance=glance,
        summary=summary,
        grounded=True,
    )


# --------------------------------------------------------------- the facts

def at_a_glance(payload: dict[str, Any]) -> dict[str, Any]:
    """Everything the officer would otherwise assemble by reading.

    Derived entirely from the stored verdict, so it cannot disagree with it.
    """
    completeness = payload.get("completeness") or {}
    flags = payload.get("flags") or []
    checks = completeness.get("checks") or []

    errors = [f for f in flags if f.get("severity") == "ERROR"]
    warnings = [f for f in flags if f.get("severity") == "WARNING"]

    # Which documents the blocking findings actually sit in, deduplicated and
    # in the order the flags raised them.
    blocking: list[dict[str, str]] = []
    for flag in errors:
        for document in flag.get("documents") or []:
            if not any(entry["key"] == document.get("key") for entry in blocking):
                blocking.append(
                    {
                        "key": document.get("key", ""),
                        "label_fr": document.get("label_fr", document.get("key", "")),
                    }
                )

    return {
        "status": payload.get("status"),
        "completeness_status": completeness.get("status"),
        "transaction_fr": completeness.get("display_name_fr"),
        "official_reference": completeness.get("official_reference"),
        "errors": len(errors),
        "warnings": len(warnings),
        "checks_passed": sum(1 for c in checks if c.get("outcome") == "PASS"),
        "checks_total": len(checks),
        "documents_present": len(completeness.get("present_documents") or []),
        "documents_missing": [
            {
                "key": m.get("key", ""),
                "label_fr": m.get("label_fr", m.get("key", "")),
            }
            for m in completeness.get("missing_documents") or []
        ],
        "blocking_documents": blocking,
        "waiting_hours": _waiting_hours(payload),
        "reviewed": bool(payload.get("reviews")),
    }


def _waiting_hours(payload: dict[str, Any]) -> float | None:
    raw = payload.get("created_at")
    if not raw:
        return None
    try:
        created = datetime.fromisoformat(str(raw))
    except ValueError:
        return None
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    return round((datetime.now(UTC) - created).total_seconds() / 3600, 1)


def _deterministic_summary(glance: dict[str, Any]) -> str:
    """Used when the corpus or the model is unavailable.

    Says only what the rules engine already decided, which is the one thing
    that is certainly true without either of them.
    """
    if glance["documents_missing"]:
        listed = ", ".join(entry["label_fr"] for entry in glance["documents_missing"])
        return f"Dossier incomplet. Pièces manquantes : {listed}."
    if glance["errors"]:
        listed = ", ".join(entry["label_fr"] for entry in glance["blocking_documents"])
        return (
            f"{glance['errors']} anomalie(s) bloquante(s)"
            + (f", sur : {listed}." if listed else ".")
        )
    if glance["warnings"]:
        return f"{glance['warnings']} point(s) à vérifier, aucun blocage automatique."
    return (
        f"Aucune anomalie. {glance['checks_passed']} vérifications sur "
        f"{glance['checks_total']} sans réserve."
    )


def _verdict_text(payload: dict[str, Any]) -> str:
    completeness = payload.get("completeness") or {}
    lines = [
        f"Statut: {completeness.get('status', 'UNKNOWN')}",
        f"Transaction: {completeness.get('display_name_fr', '')}",
    ]

    missing = completeness.get("missing_documents") or []
    if missing:
        lines.append(
            "Documents manquants: "
            + ", ".join(m.get("label_fr", m.get("key", "")) for m in missing)
        )

    for flag in payload.get("flags") or []:
        documents = ", ".join(
            d.get("label_fr", "") for d in flag.get("documents") or []
        )
        lines.append(
            f"  - [{flag.get('severity')}] {flag.get('message_fr', '')}"
            + (f" (pièce: {documents})" if documents else "")
        )

    if not missing and not payload.get("flags"):
        lines.append("Aucune anomalie détectée.")

    return "\n".join(lines)


def _query(payload: dict[str, Any]) -> str:
    """Retrieve on this dossier's procedure and its problems.

    The transaction name leads the query. Without it a clean Modification
    Entreprise retrieved the annual-statements entry -- nothing in the dossier
    to search on, so the query fell back to a generic string -- and the brief
    then described états financiers on a manager change.
    """
    completeness = payload.get("completeness") or {}
    parts = [str(completeness.get("display_name_fr") or "")]
    parts += [
        str(m.get("label_fr", "")) for m in completeness.get("missing_documents") or []
    ]
    parts += [str(f.get("message_fr", "")) for f in payload.get("flags") or []]
    return " ".join(part for part in parts if part)[:1000]
