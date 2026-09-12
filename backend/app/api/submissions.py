"""Submission intake, officer queue, and review endpoints."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.api.auth import current_officer, optional_user
from app.core.rate_limit import SUBMISSION_LIMIT, enforce
from app.core.uploads import validate_batch, validate_upload
from app.models.submission import (
    DEFAULT_UPLOAD_DIR,
    ReviewAction,
    Submission,
    SubmissionStatus,
    SubmissionStore,
    get_store,
)
from app.models.user import User, UserRole
from app.services.ocr_service import OCRService
from app.services.rules_engine import (
    COMPANY_TYPES,
    TRANSACTION_RULES,
    Status,
    UnknownTransactionType,
    check_completeness,
    required_documents_for,
)
from app.services.scoring import flag_summary, flags_from_result

logger = logging.getLogger(__name__)
router = APIRouter(tags=["submissions"])


def get_upload_dir() -> Path:
    """Where uploads are stored. A dependency so tests can redirect it."""
    return DEFAULT_UPLOAD_DIR


# ------------------------------------------------------------------ schemas

class ReviewRequest(BaseModel):
    action: ReviewAction
    note: str = Field(default="", max_length=2000)


class ContextField(BaseModel):
    """A question the applicant answers before uploading.

    Some rules cannot be evaluated from the documents -- a company's legal form
    and its fiscal year close are declared, not extracted. The frontend renders
    this list generically, so a new workflow needs no frontend change.
    """

    name: str
    label_fr: str
    label_ar: str
    type: str  # "select" | "date" | "checkbox"
    required: bool = True
    options: list[dict[str, str]] = []
    help_fr: str | None = None


class TransactionInfo(BaseModel):
    transaction_type: str
    display_name_fr: str
    display_name_ar: str
    official_reference: str
    required_documents: list[dict[str, str]]
    # Documents required only under some answers to the context fields.
    conditional_documents: list[str] = []
    checks: list[str]
    context_fields: list[ContextField] = []


class StatsResponse(BaseModel):
    total: int
    by_status: dict[str, int]
    reviewed: int
    flagged: int
    flag_rate: float = Field(description="Share of submissions carrying >=1 flag")
    average_review_seconds: float | None
    average_flags_per_submission: float


# -------------------------------------------------------------- transactions

# Context questions per workflow. Declared here rather than in the rules engine
# because they describe a form, not a rule.
CONTEXT_FIELDS: dict[str, list[ContextField]] = {
    "RNE_FINANCIAL_STATEMENTS": [
        ContextField(
            name="company_type",
            label_fr="Forme juridique",
            label_ar="الشكل القانوني",
            type="select",
            options=[
                {"value": key, "label_fr": names["fr"], "label_ar": names["ar"]}
                for key, names in COMPANY_TYPES.items()
            ],
            help_fr=(
                "Détermine si le rapport du commissaire aux comptes est requis "
                "et le montant de la pénalité de retard."
            ),
        ),
        ContextField(
            name="fiscal_year_end",
            label_fr="Date de clôture de l'exercice",
            label_ar="تاريخ ختم السنة المحاسبية",
            type="date",
            help_fr="Le dépôt est dû dans les 7 mois suivant cette date.",
        ),
        ContextField(
            name="auditor_required",
            label_fr="La société dépasse les seuils imposant un commissaire aux comptes",
            label_ar="الشركة تتجاوز العتبات الموجبة لمراقب حسابات",
            type="checkbox",
            required=False,
            help_fr="À cocher pour une SARL concernée. Inutile pour une SA ou une SCA.",
        ),
    ],
}

CONDITIONAL_DOCUMENTS: dict[str, list[str]] = {
    "RNE_FINANCIAL_STATEMENTS": ["auditor_report"],
}


@router.get("/transactions", response_model=list[TransactionInfo])
def list_transactions() -> list[TransactionInfo]:
    """Transaction types Sahilli can pre-validate, for the MSME landing page."""
    from app.services.rules_engine import DOCUMENT_LABELS

    return [
        TransactionInfo(
            transaction_type=key,
            display_name_fr=rules["display_name_fr"],
            display_name_ar=rules["display_name_ar"],
            official_reference=rules["official_reference"],
            required_documents=[
                {
                    "key": doc,
                    "label_fr": DOCUMENT_LABELS.get(doc, {}).get("fr", doc),
                    "label_ar": DOCUMENT_LABELS.get(doc, {}).get("ar", doc),
                }
                for doc in rules["required_documents"]
            ],
            conditional_documents=CONDITIONAL_DOCUMENTS.get(key, []),
            checks=rules["checks"],
            context_fields=CONTEXT_FIELDS.get(key, []),
        )
        for key, rules in TRANSACTION_RULES.items()
    ]


# ------------------------------------------------------------------- intake

@router.post(
    "/transactions/{transaction_type}/submissions",
    status_code=status.HTTP_201_CREATED,
)
async def create_submission(
    request: Request,
    transaction_type: str,
    # NOTE: these must be declared as bare `list[...]`. Writing `list[str] | None`
    # makes FastAPI treat the field as a single optional value, so repeated form
    # entries silently collapse to one and only one document is registered.
    files: Annotated[list[UploadFile], File(description="Uploaded documents")] = [],
    document_types: Annotated[
        list[str],
        Form(description="Document key per file, parallel to `files`"),
    ] = [],
    submitted_at: Annotated[str | None, Form()] = None,
    # Workflow context. Declared rather than extracted: a company's legal form
    # and fiscal year close are not reliably readable from the documents.
    company_type: Annotated[str | None, Form()] = None,
    fiscal_year_end: Annotated[str | None, Form()] = None,
    auditor_required: Annotated[bool, Form()] = False,
    store: SubmissionStore = Depends(get_store),
    upload_dir: Path = Depends(get_upload_dir),
    user: User | None = Depends(optional_user),
) -> dict[str, Any]:
    """Accept documents, run OCR + completeness + flagging, return the verdict.

    `document_types[i]` names what `files[i]` is (see TRANSACTION_RULES
    required_documents). Types are supplied by the caller, never guessed, so the
    OCR prompt can be specialised per document.
    """
    if transaction_type not in TRANSACTION_RULES:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown transaction type '{transaction_type}'. "
            f"Known: {', '.join(TRANSACTION_RULES)}",
        )

    enforce(request, "submission", SUBMISSION_LIMIT)

    files = files or []
    document_types = document_types or []

    # A document type outside the transaction's own list would be stored under
    # an arbitrary directory name and silently ignored by the rules engine.
    allowed = set(TRANSACTION_RULES[transaction_type]["required_documents"])
    unknown = sorted({d for d in document_types if d not in allowed})
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Type de document inconnu pour cette démarche : "
                f"{', '.join(unknown)}."
            ),
        )

    if len(files) != len(document_types):
        raise HTTPException(
            status_code=400,
            detail=f"Received {len(files)} files but {len(document_types)} document "
            "types; they must be parallel lists.",
        )

    ocr = OCRService()
    documents: dict[str, Any] = {}
    total_bytes = 0

    for upload, doc_type in zip(files, document_types):
        content = await upload.read()
        # Validate before writing anything: the declared Content-Type is
        # attacker-controlled, so the file's own bytes decide what it is.
        detected_type = validate_upload(content, upload.filename or doc_type)
        total_bytes += len(content)
        validate_batch(len(files), total_bytes)

        stored_path = _persist(content, upload.filename or doc_type, doc_type, upload_dir)
        # OCR is synchronous and can take seconds per page. Called directly it
        # would block the event loop and stall every other request behind it.
        result = await run_in_threadpool(
            ocr.extract, content, upload.filename or "", doc_type
        )

        documents[doc_type] = {
            "filename": Path(upload.filename or doc_type).name,
            "stored_path": stored_path.name,
            "content_type": detected_type,
            "size_bytes": len(content),
            **result.to_dict(),
        }

    context: dict[str, Any] = {}
    if company_type:
        context["company_type"] = company_type.upper()
    if fiscal_year_end:
        context["fiscal_year_end"] = fiscal_year_end
    if auditor_required:
        context["auditor_required"] = True

    submission_payload = {
        "transaction_type": transaction_type,
        "documents": documents,
        "submitted_at": submitted_at,
        **context,
    }

    try:
        completeness = check_completeness(
            submission_payload,
            today=_parse_iso_date(submitted_at),
        )
    except UnknownTransactionType as exc:  # pragma: no cover - guarded above
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    flags = flags_from_result(completeness)

    submission = store.create(
        transaction_type=transaction_type,
        documents=documents,
        completeness=completeness.to_dict(),
        flags=[flag.to_dict() for flag in flags],
        status=_initial_status(completeness.status).value,
        submitted_at=submitted_at,
        context=context,
        owner_id=str(user.id) if user else None,
    )

    return {
        "submission_id": submission.id,
        "status": submission.status,
        "required_documents": required_documents_for(
            TRANSACTION_RULES[transaction_type], submission_payload
        ),
        "completeness": submission.completeness,
        "flags": submission.flags,
        "flag_summary": flag_summary(flags),
    }


def _initial_status(completeness_status: Status) -> SubmissionStatus:
    """A filing that passes every rule is PRE_VALIDATED; otherwise SUBMITTED.

    Pre-validation is Sahilli's whole point: the MSME learns before the registry
    ever sees it whether the file would survive intake.
    """
    return (
        SubmissionStatus.PRE_VALIDATED
        if completeness_status is Status.COMPLETE
        else SubmissionStatus.SUBMITTED
    )


def _persist(content: bytes, filename: str, doc_type: str, upload_dir: Path) -> Path:
    """Store the upload under <upload_dir>/<doc_type>/ with a unique name."""
    safe_name = Path(filename).name or f"{doc_type}.bin"
    directory = upload_dir / doc_type
    directory.mkdir(parents=True, exist_ok=True)

    # Derive the suffix from the ORIGINAL name each time. Re-stemming the
    # already-suffixed candidate compounds it into name_1_2_3_... until the
    # filename exceeds the filesystem limit.
    base = Path(safe_name)
    destination = directory / safe_name
    counter = 1
    while destination.exists():
        destination = directory / f"{base.stem}_{counter}{base.suffix}"
        counter += 1

    destination.write_bytes(content)
    return destination


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


# ---------------------------------------------------------------- documents

@router.get("/documents/{document_type}/{filename}")
def get_document(
    document_type: str,
    filename: str,
    upload_dir: Path = Depends(get_upload_dir),
    officer: User = Depends(current_officer),
) -> FileResponse:
    """Serve an uploaded document so the officer can read it beside the
    extracted fields.

    Both path segments come from the URL, so they are treated as hostile: we
    take only the final path component of each and then confirm the resolved
    file really sits inside the upload directory. That blocks `../` traversal
    and absolute paths, including forms that survive one round of stripping.
    """
    safe_type = Path(document_type).name
    safe_name = Path(filename).name
    if not safe_type or not safe_name:
        raise HTTPException(status_code=404, detail="Document not found")

    root = upload_dir.resolve()
    candidate = (root / safe_type / safe_name).resolve()

    if not candidate.is_relative_to(root) or not candidate.is_file():
        raise HTTPException(status_code=404, detail="Document not found")

    return FileResponse(candidate)


# -------------------------------------------------------------------- queue

@router.get("/submissions")
def list_submissions(
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    transaction_type: Annotated[str | None, Query()] = None,
    store: SubmissionStore = Depends(get_store),
    officer: User = Depends(current_officer),
) -> dict[str, Any]:
    """Officer queue, newest first, filterable by status and transaction type.

    Officer-only: the queue lists every applicant's filing and its anomalies.
    """
    submissions = store.list(status=status_filter, transaction_type=transaction_type)
    return {
        "count": len(submissions),
        "submissions": [s.to_summary() for s in submissions],
    }


@router.get("/submissions/stats", response_model=StatsResponse)
def submission_stats(
    store: SubmissionStore = Depends(get_store),
    officer: User = Depends(current_officer),
) -> StatsResponse:
    """Live dashboard figures, computed from stored submissions.

    Declared before /submissions/{submission_id} so "stats" is not captured as
    an ID by the path parameter.
    """
    submissions = store.list()
    total = len(submissions)

    by_status: dict[str, int] = {}
    for submission in submissions:
        by_status[submission.status] = by_status.get(submission.status, 0) + 1

    latencies = [
        latency
        for submission in submissions
        if (latency := submission.review_latency_seconds()) is not None
    ]
    flagged = sum(1 for s in submissions if s.flag_count > 0)
    total_flags = sum(s.flag_count for s in submissions)

    return StatsResponse(
        total=total,
        by_status=by_status,
        reviewed=len(latencies),
        flagged=flagged,
        flag_rate=round(flagged / total, 4) if total else 0.0,
        average_review_seconds=(
            round(sum(latencies) / len(latencies), 2) if latencies else None
        ),
        average_flags_per_submission=round(total_flags / total, 2) if total else 0.0,
    )


@router.get("/submissions/{submission_id}")
def get_submission(
    submission_id: str,
    store: SubmissionStore = Depends(get_store),
    user: User | None = Depends(optional_user),
) -> dict[str, Any]:
    """Full detail: status, extracted fields, flags, and review history.

    Readable by an officer, by the applicant who filed it, or by anyone holding
    the id of a guest filing. That last case is a capability URL: guest filings
    have no owner to check against, and the id is a random 12-hex token. It is
    the price of letting people check a dossier without an account -- an
    accounts-only product would drop this branch.
    """
    submission = _require(store.get(submission_id), submission_id)

    owner_id = submission.owner_id
    is_owner = user is not None and str(user.id) == owner_id
    is_officer = user is not None and user.role == UserRole.OFFICER.value

    if owner_id and not (is_owner or is_officer):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce dossier ne vous appartient pas.",
        )

    return submission.to_dict()


@router.post("/submissions/{submission_id}/review")
def review_submission(
    submission_id: str,
    request: ReviewRequest,
    store: SubmissionStore = Depends(get_store),
    officer: User = Depends(current_officer),
) -> dict[str, Any]:
    """Officer decision: approve, reject, or request a correction.

    Officer-only. This endpoint decides whether a citizen's filing is accepted;
    leaving it open would let anyone approve or reject any dossier.
    """
    _require(store.get(submission_id), submission_id)

    # The acting officer comes from the session, never from the request body --
    # otherwise the audit trail is whatever the caller typed.
    updated = store.add_review(
        submission_id, request.action, note=request.note, officer=officer.email
    )
    updated = _require(updated, submission_id)
    return {
        "submission_id": updated.id,
        "status": updated.status,
        "reviews": updated.reviews,
    }


def _require(submission: Submission | None, submission_id: str) -> Submission:
    if submission is None:
        raise HTTPException(status_code=404, detail=f"No submission '{submission_id}'")
    return submission
