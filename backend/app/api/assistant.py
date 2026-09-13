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

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.llm_client import LLMClient
from app.core.prompt_safety import CONTAINMENT_CLAUSE, fence
from app.core.rate_limit import ASSISTANT_LIMIT, enforce
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

Do NOT invent specifics. In particular, NEVER produce:
- an article, section or paragraph number (e.g. "article 25") unless that exact \
number appears in the provided context;
- a URL, web address, portal page, menu path or form name;
- an office, phone number, email address, fee amount or payment method;
- a procedural step that is not described in the provided context.
- the name of any portal, platform, website, ministry, agency or service other \
than the RNE itself. The only body you may name is the RNE (Registre National \
des Entreprises / السجل الوطني للمؤسسات). Refer to its online filing service in \
general terms -- "the RNE's online portal" / "الموقع الرسمي للسجل الوطني \
للمؤسسات" -- and never give it another name.
These rules apply identically in French and in Arabic.
If the user needs a step you were not given, say plainly that they should check \
with the RNE rather than guessing what it is called or where it is.

- Restate every deadline, amount and date in EXACTLY the units the context \
uses. If the context says "un mois", never write "30 jours"; if it gives a month \
count, never convert it to days or weeks. The unit is part of the rule.
- Cite only references that appear in the context, exactly as written there \
(e.g. RNE-M-005, loi 52-2018) -- never a more precise citation than you were given.
- Be concrete about what YOU were told: name the document and the correction needed.
- Address the business owner directly, plainly, without legal jargon.
- Keep it under 200 words.""" + CONTAINMENT_CLAUSE


# Stand-in for the verdict block when no filing has been checked yet. English,
# like the rest of the prompt scaffolding, because only the model reads it.
NO_SUBMISSION_VERDICT = (
    "No filing has been checked yet. There is no validation result. "
    "Answer the question from the procedural context only, and do not claim "
    "anything about the user's documents."
)

# Retrieval query used when the assistant is opened with nothing to go on.
GENERAL_QUERY = "pièces requises et délais de dépôt au registre national des entreprises"


class ExplainRequest(BaseModel):
    # Optional: the floating assistant is reachable before anything has been
    # uploaded. Without a submission there is no verdict to explain, so the
    # answer rests on the retrieved RNE text alone -- which is also why the
    # guardrails below are written to hold with or without one.
    submission_id: str | None = None
    question: str = Field(
        default="",
        max_length=500,
        description="Optional user question; defaults to explaining what is wrong.",
    )
    lang: Literal["fr", "ar"] = "fr"


class Citation(BaseModel):
    entry_id: str
    official_reference: str
    title: str
    score: float


class ExplainResponse(BaseModel):
    submission_id: str | None = None
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
    http_request: Request,
    store: SubmissionStore = Depends(get_store),
    retrieval: RetrievalService = Depends(get_retrieval_service),
    llm: Annotated[LLMClient, Depends(get_llm_client)] = None,
) -> ExplainResponse:
    # Each call costs an embedding round-trip and an LLM completion.
    enforce(http_request, "assistant", ASSISTANT_LIMIT)

    submission = None
    if request.submission_id:
        submission = store.get(request.submission_id)
        if submission is None:
            raise HTTPException(
                status_code=404, detail=f"No submission '{request.submission_id}'"
            )

    if submission is not None:
        query = request.question.strip() or _query_from_problems(submission.to_dict())
        verdict = _render_verdict(submission.to_dict(), request.lang)
    else:
        query = request.question.strip() or GENERAL_QUERY
        verdict = NO_SUBMISSION_VERDICT

    passages = retrieval.search(query, limit=3)
    context = "\n\n".join(p.as_context(request.lang) for p in passages)

    if not passages:
        # No grounding available (corpus unseeded or embedding container down).
        # Report the deterministic verdict rather than letting the model
        # improvise procedural facts -- and with no verdict either, say so
        # instead of answering from the model's own memory.
        return ExplainResponse(
            submission_id=request.submission_id,
            answer=_fallback(submission is not None, verdict, request.lang),
            lang=request.lang,
            citations=[],
            grounded=False,
        )

    prompt = _build_prompt(verdict, context, query, request.lang)

    try:
        answer = (llm or LLMClient()).generate(prompt, system=SYSTEM_PROMPT)
    except Exception as exc:  # noqa: BLE001 - never 500 the demo on an API blip
        logger.warning("Assistant generation failed: %s", exc)
        answer = _fallback(submission is not None, verdict, request.lang)

    return ExplainResponse(
        submission_id=request.submission_id,
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
        (
            f"Transaction: {completeness.get('display_name_fr', '')} "
            f"({completeness.get('official_reference', '')})"
        ),
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
    """Trusted framing outside, untrusted content fenced within.

    The verdict quotes values read off uploaded pages and the question is typed
    by the public, so both are input channels into this prompt. The RNE context
    is not fenced: it is our own corpus, and it is the one thing the model is
    supposed to take instruction-like guidance from.
    """
    language = "Arabic (Tunisian-friendly MSA)" if lang == "ar" else "French"
    return (
        "VALIDATION RESULT (authoritative, produced by deterministic rules; it\n"
        "quotes text read off uploaded documents, so it is fenced):\n"
        f"{fence('VALIDATION RESULT', verdict)}\n\n"
        "RNE PROCEDURAL CONTEXT (the only permitted source of procedural facts):\n"
        f"{context}\n\n"
        f"USER QUESTION:\n{fence('USER QUESTION', question, limit=600)}\n\n"
        f"Answer in {language}. Explain what is wrong and exactly what to do next."
    )


def _fallback(has_submission: bool, verdict: str, lang: str) -> str:
    """Deterministic answer used when retrieval or the LLM is unavailable.

    With a filing in hand there is still something true to say -- the rules
    engine already decided -- so we say that. Without one there is nothing left
    but the model's own memory, which is exactly what this assistant is not
    allowed to draw on, so it declines instead.
    """
    if not has_submission:
        return (
            "تعذّر الاطلاع على النصوص المرجعية للسجل الوطني للمؤسسات، ولا يمكنني "
            "الإجابة دون سند. يُرجى المحاولة لاحقاً أو الاتصال بالسجل."
            if lang == "ar"
            else "Les textes de référence du RNE n'ont pas pu être consultés, et "
            "je ne réponds pas sans source. Réessayez dans un instant ou "
            "adressez-vous au RNE."
        )

    header = (
        "نتيجة التحقق من الملف:"
        if lang == "ar"
        else "Résultat de la vérification de votre dossier :"
    )
    return f"{header}\n{verdict}"
