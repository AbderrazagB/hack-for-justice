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
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.models.submission import (
    DEFAULT_UPLOAD_DIR,
    ReviewAction,
    Submission,
    SubmissionStatus,
    SubmissionStore,
    get_store,
)
from app.services.ocr_service import OCRService
from app.services.rules_engine import (
    TRANSACTION_RULES,
    Status,
    UnknownTransactionType,
    check_completeness,
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
    note: str = ""
    officer: str = "officer"


class TransactionInfo(BaseModel):
    transaction_type: str
    display_name_fr: str
    display_name_ar: str
    official_reference: str
    required_documents: list[dict[str, str]]
    checks: list[str]


class StatsResponse(BaseModel):
    total: int
    by_status: dict[str, int]
    reviewed: int
    flagged: int
    flag_rate: float = Field(description="Share of submissions carrying >=1 flag")
    average_review_seconds: float | None
    average_flags_per_submission: float


# -------------------------------------------------------------- transactions

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
            checks=rules["checks"],
        )
        for key, rules in TRANSACTION_RULES.items()
    ]


# ------------------------------------------------------------------- intake

@router.post(
    "/transactions/{transaction_type}/submissions",
    status_code=status.HTTP_201_CREATED,
)
async def create_submission(
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
    store: SubmissionStore = Depends(get_store),
    upload_dir: Path = Depends(get_upload_dir),
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

    files = files or []
    document_types = document_types or []
    if len(files) != len(document_types):
        raise HTTPException(
            status_code=400,
            detail=f"Received {len(files)} files but {len(document_types)} document "
            "types; they must be parallel lists.",
        )

    ocr = OCRService()
    documents: dict[str, Any] = {}

    for upload, doc_type in zip(files, document_types):
        content = await upload.read()
        stored_path = _persist(content, upload.filename or doc_type, doc_type, upload_dir)
        result = ocr.extract(content, upload.filename or "", doc_type)

        documents[doc_type] = {
            "filename": Path(upload.filename or doc_type).name,
            "stored_path": stored_path.name,
            "content_type": upload.content_type,
            "size_bytes": len(content),
            **result.to_dict(),
        }

    submission_payload = {
        "transaction_type": transaction_type,
        "documents": documents,
        "submitted_at": submitted_at,
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
    )

    return {
        "submission_id": submission.id,
        "status": submission.status,
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
) -> dict[str, Any]:
    """Officer queue, newest first, filterable by status and transaction type."""
    submissions = store.list(status=status_filter, transaction_type=transaction_type)
    return {
        "count": len(submissions),
        "submissions": [s.to_summary() for s in submissions],
    }


@router.get("/submissions/stats", response_model=StatsResponse)
def submission_stats(store: SubmissionStore = Depends(get_store)) -> StatsResponse:
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
    submission_id: str, store: SubmissionStore = Depends(get_store)
) -> dict[str, Any]:
    """Full detail: status, extracted fields, flags, and review history."""
    submission = _require(store.get(submission_id), submission_id)
    return submission.to_dict()


@router.post("/submissions/{submission_id}/review")
def review_submission(
    submission_id: str,
    request: ReviewRequest,
    store: SubmissionStore = Depends(get_store),
) -> dict[str, Any]:
    """Officer decision: approve, reject, or request a correction."""
    _require(store.get(submission_id), submission_id)

    updated = store.add_review(
        submission_id, request.action, note=request.note, officer=request.officer
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
