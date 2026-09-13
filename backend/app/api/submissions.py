"""Submission intake, officer queue, and review endpoints."""

from __future__ import annotations

import json
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
from fastapi.responses import FileResponse, Response
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
from app.services.declaration import (
    DECLARATION_FIELDS,
    FIELD_GROUPS,
    MODIFICATION_TYPES,
    TRANSACTION_MODIFICATION_TYPE,
)
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


class DeclarationFieldInfo(BaseModel):
    """One field of RNE-F-005, described so the frontend can render the form."""

    name: str
    label_fr: str
    label_ar: str
    type: str
    required: bool
    help_fr: str | None = None
    # Static, per-field justification. Shown on demand next to the question so
    # an applicant can see why it is asked without having to ask anything.
    why_fr: str | None = None
    why_ar: str | None = None
    # Section the question belongs to, and -- for the three answers actually
    # compared against a document -- which document.
    group: str = "entity"
    group_fr: str = ""
    group_ar: str = ""
    cross_checked: bool = False
    compared_with_fr: str | None = None
    compared_with_ar: str | None = None


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
    # RNE-F-005: the declaration the applicant signs, captured as questions
    # rather than asked for as a PDF they must find and decipher.
    declaration_fields: list[DeclarationFieldInfo] = []
    modification_type_fr: str | None = None
    modification_type_ar: str | None = None


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
            name="ago_not_held",
            label_fr="L'assemblée générale n'a pas encore approuvé les comptes",
            label_ar="لم تصادق الجلسة العامة على الحسابات بعد",
            type="checkbox",
            required=False,
            help_fr=(
                "Le RNE accepte le dépôt des états financiers seuls avant "
                "l'échéance ; le procès-verbal sera à déposer ensuite."
            ),
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
    "RNE_FINANCIAL_STATEMENTS": ["auditor_report", "general_assembly_pv_approval"],
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
            declaration_fields=[
                DeclarationFieldInfo(
                    name=spec.name,
                    label_fr=spec.label_fr,
                    label_ar=spec.label_ar,
                    type=spec.type,
                    required=spec.required,
                    help_fr=spec.help_fr,
                    why_fr=spec.why_fr,
                    why_ar=spec.why_ar,
                    group=spec.group,
                    group_fr=FIELD_GROUPS[spec.group]["fr"],
                    group_ar=FIELD_GROUPS[spec.group]["ar"],
                    cross_checked=spec.cross_checked,
                    compared_with_fr=spec.compared_with_fr,
                    compared_with_ar=spec.compared_with_ar,
                )
                for spec in DECLARATION_FIELDS
            ],
            modification_type_fr=_modification_label(key, "fr"),
            modification_type_ar=_modification_label(key, "ar"),
        )
        for key, rules in TRANSACTION_RULES.items()
    ]


def _modification_label(transaction_type: str, lang: str) -> str | None:
    """Which box this procedure ticks in RNE-F-005's modification grid."""
    key = TRANSACTION_MODIFICATION_TYPE.get(transaction_type)
    return MODIFICATION_TYPES.get(key, {}).get(lang) if key else None


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
    ago_not_held: Annotated[bool, Form()] = False,
    # RNE-F-005 answers, JSON-encoded: a multipart form cannot carry a nested
    # object, and the alternative is nine more flat fields per workflow.
    declaration: Annotated[str | None, Form()] = None,
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
    if ago_not_held:
        context["ago_not_held"] = True

    declared: dict[str, Any] = {}
    if declaration:
        try:
            parsed = json.loads(declaration)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400, detail="Déclaration illisible."
            ) from None
        if not isinstance(parsed, dict):
            raise HTTPException(
                status_code=400, detail="Déclaration invalide."
            )
        # Keep only the form's own fields, trimmed and length-capped: this goes
        # into a stored document and a generated PDF.
        known = {spec.name for spec in DECLARATION_FIELDS}
        declared = {
            key: str(value).strip()[:200]
            for key, value in parsed.items()
            if key in known and value not in (None, "")
        }

    submission_payload = {
        "transaction_type": transaction_type,
        "documents": documents,
        "submitted_at": submitted_at,
        "declaration": declared,
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
        context={**context, "declaration": declared} if declared else context,
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


@router.get("/submissions/{submission_id}/declaration.pdf")
def declaration_sheet(
    submission_id: str,
    store: SubmissionStore = Depends(get_store),
    user: User | None = Depends(optional_user),
) -> Response:
    """The applicant's preparation sheet for RNE-F-005.

    Same access rule as the submission itself. Explicitly not a filing: the
    sheet says so on its own first page.
    """
    submission = _require(store.get(submission_id), submission_id)
    _assert_may_read(submission, user)

    from app.services.declaration_pdf import build_preparation_sheet

    payload = submission.to_dict()
    payload["modification_type_fr"] = _modification_label(
        submission.transaction_type, "fr"
    )
    pdf = build_preparation_sheet(payload)

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="sahilli-preparation-{submission.id}.pdf"'
            )
        },
    )


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
    _assert_may_read(submission, user)
    return submission.to_dict()


def _assert_may_read(submission: Submission, user: User | None) -> None:
    """An officer, the owner, or anyone holding a guest filing's id."""
    owner_id = submission.owner_id
    is_owner = user is not None and str(user.id) == owner_id
    is_officer = user is not None and user.role == UserRole.OFFICER.value

    if owner_id and not (is_owner or is_officer):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce dossier ne vous appartient pas.",
        )


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
