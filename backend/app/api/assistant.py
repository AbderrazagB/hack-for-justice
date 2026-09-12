"""Grounded explanation endpoint.

The assistant explains what is wrong with a filing in plain FR/AR. It is
deliberately constrained: the verdict always comes from the deterministic rules
engine, and the procedural facts always come from retrieved RNE text. The model
rewrites those two inputs into something a non-lawyer can act on -- it never
decides whether a filing is valid and never supplies a deadline or penalty from
its own knowledge.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.llm_client import LLMClient
from app.models.submission import SubmissionStore, get_store
from app.services.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["assistant"])

SYSTEM_PROMPT = """You are Sahilli, an assistant that helps Tunisian MSMEs fix \
business-registry filings before they are submitted to the RNE.

Absolute rules:
- Use ONLY the VALIDATION RESULT and the RNE PROCEDURAL CONTEXT provided below.
- NEVER state a deadline, penalty, fee, or document requirement that is not in \
the provided context. If the context does not cover the question, say you do not \
have that information and suggest contacting the RNE.
- NEVER contradict the validation result. It is authoritative.
- Cite the official reference (e.g. RNE-M-005, loi 52-2018) when you rely on it.
- Be concrete and practical: name the document and the exact action needed.
- Address the business owner directly, plainly, without legal jargon.
- Keep it under 200 words."""


class ExplainRequest(BaseModel):
    submission_id: str
    question: str = Field(
        default="",
        description="Optional user question; defaults to explaining what is wrong.",
    )
    lang: Literal["fr", "ar"] = "fr"


class Citation(BaseModel):
    entry_id: str
    official_reference: str
    title: str
    score: float


class ExplainResponse(BaseModel):
    submission_id: str
    answer: str
    lang: str
    citations: list[Citation]
    grounded: bool = Field(
        description="False when no procedural context could be retrieved."
    )


def get_retrieval_service() -> RetrievalService:
    return RetrievalService()


def get_llm_client() -> LLMClient:
    return LLMClient()


@router.post("/assistant/explain", response_model=ExplainResponse)
def explain(
    request: ExplainRequest,
    store: SubmissionStore = Depends(get_store),
    retrieval: RetrievalService = Depends(get_retrieval_service),
    llm: Annotated[LLMClient, Depends(get_llm_client)] = None,
) -> ExplainResponse:
    submission = store.get(request.submission_id)
    if submission is None:
        raise HTTPException(
            status_code=404, detail=f"No submission '{request.submission_id}'"
        )

    query = request.question.strip() or _query_from_problems(submission.to_dict())
    passages = retrieval.search(query, limit=3)

    verdict = _render_verdict(submission.to_dict(), request.lang)
    context = "\n\n".join(p.as_context(request.lang) for p in passages)

    if not passages:
        # No grounding available (corpus unseeded or embedding container down).
        # Report the deterministic verdict rather than letting the model
        # improvise procedural facts.
        return ExplainResponse(
            submission_id=submission.id,
            answer=_ungrounded_fallback(verdict, request.lang),
            lang=request.lang,
            citations=[],
            grounded=False,
        )

    prompt = _build_prompt(verdict, context, query, request.lang)

    try:
        answer = (llm or LLMClient()).generate(prompt, system=SYSTEM_PROMPT)
    except Exception as exc:  # noqa: BLE001 - never 500 the demo on an API blip
        logger.warning("Assistant generation failed: %s", exc)
        answer = _ungrounded_fallback(verdict, request.lang)

    return ExplainResponse(
        submission_id=submission.id,
        answer=answer.strip(),
        lang=request.lang,
        citations=[
            Citation(
                entry_id=p.entry_id,
                official_reference=p.official_reference,
                title=p.title_ar if request.lang == "ar" else p.title_fr,
                score=round(p.score, 4),
            )
            for p in passages
        ],
        grounded=True,
    )


# ---------------------------------------------------------------- rendering

def _query_from_problems(submission: dict[str, Any]) -> str:
    """Build a retrieval query from what actually went wrong.

    Retrieving on the problems rather than a generic string is what pulls the
    deadline entry for a late filing and the checklist entry for a missing
    document.
    """
    parts: list[str] = []
    completeness = submission.get("completeness") or {}

    for missing in completeness.get("missing_documents", []):
        parts.append(str(missing.get("label_fr", missing.get("key", ""))))
    for flag in submission.get("flags", []):
        parts.append(str(flag.get("message_fr", "")))

    if not parts:
        parts.append("pièces requises pour une modification d'entreprise au RNE")

    return " ".join(parts)[:1000]


def _render_verdict(submission: dict[str, Any], lang: str) -> str:
    """The authoritative rules-engine outcome, as text for the prompt."""
    completeness = submission.get("completeness") or {}
    lines = [
        f"Statut: {completeness.get('status', 'UNKNOWN')}",
        f"Transaction: {completeness.get('display_name_fr', '')} "
        f"({completeness.get('official_reference', '')})",
    ]

    missing = completeness.get("missing_documents") or []
    if missing:
        listed = ", ".join(
            m.get("label_ar" if lang == "ar" else "label_fr", m.get("key", ""))
            for m in missing
        )
        lines.append(f"Documents manquants: {listed}")

    flags = submission.get("flags") or []
    if flags:
        lines.append("Problèmes détectés:")
        lines += [
            f"  - [{f.get('severity')}] "
            f"{f.get('message_ar' if lang == 'ar' else 'message_fr', '')}"
            for f in flags
        ]

    if not missing and not flags:
        lines.append("Aucun problème détecté. Le dossier est complet.")

    return "\n".join(lines)


def _build_prompt(verdict: str, context: str, question: str, lang: str) -> str:
    language = "Arabic (Tunisian-friendly MSA)" if lang == "ar" else "French"
    return (
        f"VALIDATION RESULT (authoritative, produced by deterministic rules):\n"
        f"{verdict}\n\n"
        f"RNE PROCEDURAL CONTEXT (the only permitted source of procedural facts):\n"
        f"{context}\n\n"
        f"USER QUESTION:\n{question}\n\n"
        f"Answer in {language}. Explain what is wrong and exactly what to do next."
    )


def _ungrounded_fallback(verdict: str, lang: str) -> str:
    """Deterministic answer used when retrieval or the LLM is unavailable."""
    header = (
        "نتيجة التحقق من الملف:"
        if lang == "ar"
        else "Résultat de la vérification de votre dossier :"
    )
    return f"{header}\n{verdict}"
