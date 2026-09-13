"""The public API: pre-validation as a service.

What a bank, an accountant's practice or a legal-tech platform buys is the
answer to one question -- *will the registry reject this filing, and why?* --
for documents they already hold. They do not want our upload flow, our stepper
or our login screen.

So this is a separate, versioned surface rather than the app's routes with a
different guard on them. `/v1` is a contract: the app's internals can change,
this cannot without a `/v2`.

Every field an integrator reads is documented here in the response models,
because the thing being sold is the response.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from app.core.api_auth import ApiCaller, current_api_caller
from app.models.submission import SubmissionStore, get_store
from app.services.declaration import DECLARATION_FIELDS
from app.services.ocr_service import OCRService
from app.services.rules_engine import (
    DOCUMENT_LABELS,
    TRANSACTION_RULES,
    check_completeness,
)
from app.services.scoring import flag_summary, flags_from_result

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["public api"])

# What the app allows per submission, restated here so the published contract
# does not move when an internal constant does.
MAX_DOCUMENTS = 12


class CheckOutcomeModel(BaseModel):
    name: str = Field(description="Stable identifier for the rule.")
    outcome: str = Field(description="PASS, FAIL or INDETERMINATE.")
    label_fr: str
    label_ar: str
    reason_fr: str = Field(description="Why, in the applicant's terms.")
    reason_ar: str
    evidence: dict[str, Any] = Field(
        default_factory=dict, description="The values the rule compared."
    )


class FindingModel(BaseModel):
    code: str = Field(description="Matches the `name` of the rule that raised it.")
    severity: str = Field(description="ERROR blocks the filing; WARNING needs a look.")
    message_fr: str
    message_ar: str
    documents: list[dict[str, str]] = Field(
        default_factory=list, description="The pieces this finding concerns."
    )
    evidence: dict[str, Any] = Field(default_factory=dict)


class ValidationResponse(BaseModel):
    validation_id: str = Field(description="Retrieve this result again at /v1/validations/{id}.")
    transaction_type: str
    status: str = Field(
        description="COMPLETE, INCOMPLETE (a required piece is absent), or "
        "NEEDS_REVIEW (a rule failed or could not be decided)."
    )
    accepted: bool = Field(
        description="True only when every required piece is present and every "
        "rule passed. The one field to branch on."
    )
    missing_documents: list[dict[str, str]]
    checks: list[CheckOutcomeModel]
    skipped_checks: list[dict[str, str]] = Field(
        description="Rules that did not run, and why. A rule absent from "
        "`checks` without appearing here would read as one that passed."
    )
    findings: list[FindingModel]
    summary: dict[str, int]
    deadline: dict[str, Any] | None = Field(
        default=None,
        description="The legal clock when the procedure has one: date, days "
        "remaining or overdue, and the estimated penalty.",
    )
    quota: dict[str, int] = Field(description="Calls used and remaining this period.")


class TransactionModel(BaseModel):
    transaction_type: str
    display_name_fr: str
    display_name_ar: str
    official_reference: str
    required_documents: list[dict[str, str]]
    checks: list[str]
    declaration_fields: list[dict[str, Any]]


@router.get("/transactions", response_model=list[TransactionModel])
def list_transactions(caller: ApiCaller = Depends(current_api_caller)) -> list[dict[str, Any]]:
    """The procedures this API validates, and what each one needs.

    Call this first: `transaction_type` and the `key` of each required document
    are the identifiers /v1/validate expects.
    """
    return [
        {
            "transaction_type": key,
            "display_name_fr": rules["display_name_fr"],
            "display_name_ar": rules["display_name_ar"],
            "official_reference": rules["official_reference"],
            "required_documents": [
                {
                    "key": doc,
                    "label_fr": DOCUMENT_LABELS.get(doc, {}).get("fr", doc),
                    "label_ar": DOCUMENT_LABELS.get(doc, {}).get("ar", doc),
                }
                for doc in rules["required_documents"]
            ],
            "checks": rules["checks"],
            "declaration_fields": [
                {
                    "name": spec.name,
                    "label_fr": spec.label_fr,
                    "label_ar": spec.label_ar,
                    "required": spec.required,
                    "cross_checked": spec.cross_checked,
                }
                for spec in DECLARATION_FIELDS
            ],
        }
        for key, rules in TRANSACTION_RULES.items()
    ]


@router.post(
    "/validate",
    response_model=ValidationResponse,
    status_code=status.HTTP_200_OK,
)
async def validate(
    transaction_type: Annotated[str, Form(description="From /v1/transactions.")],
    files: Annotated[list[UploadFile], File(description="One file per document.")] = [],
    document_types: Annotated[
        list[str], Form(description="Document key per file, in the same order.")
    ] = [],
    declaration: Annotated[
        str | None,
        Form(description="RNE-F-005 answers as a JSON object. Optional; without "
             "it the declaration cross-check does not run and says so."),
    ] = None,
    submitted_at: Annotated[
        str | None, Form(description="YYYY-MM-DD. Defaults to today. Deadlines are "
                         "computed against this date.")
    ] = None,
    company_type: Annotated[str | None, Form()] = None,
    fiscal_year_end: Annotated[str | None, Form()] = None,
    caller: ApiCaller = Depends(current_api_caller),
    store: SubmissionStore = Depends(get_store),
) -> dict[str, Any]:
    """Validate a set of documents against a procedure's rules.

    Synchronous, and it reads every page, so budget on the order of fifteen
    seconds per document. Nothing is filed anywhere: this answers whether the
    registry would reject the dossier, which is a different thing from
    submitting it.
    """
    if transaction_type not in TRANSACTION_RULES:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown transaction_type '{transaction_type}'. "
            f"Known: {', '.join(TRANSACTION_RULES)}",
        )

    files = files or []
    document_types = document_types or []
    if len(files) != len(document_types):
        raise HTTPException(
            status_code=400,
            detail=f"{len(files)} file(s) but {len(document_types)} document_types.",
        )
    if len(files) > MAX_DOCUMENTS:
        raise HTTPException(
            status_code=400, detail=f"At most {MAX_DOCUMENTS} documents per call."
        )

    allowed = set(TRANSACTION_RULES[transaction_type]["required_documents"])
    unknown = sorted({d for d in document_types if d not in allowed})
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"document_types not part of {transaction_type}: {', '.join(unknown)}",
        )

    declared: dict[str, Any] = {}
    if declaration:
        try:
            parsed = json.loads(declaration)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400, detail="`declaration` is not valid JSON."
            ) from None
        if not isinstance(parsed, dict):
            raise HTTPException(status_code=400, detail="`declaration` must be an object.")
        known = {spec.name for spec in DECLARATION_FIELDS}
        declared = {
            key: str(value).strip()[:200]
            for key, value in parsed.items()
            if key in known and value not in (None, "")
        }

    from app.api.submissions import _persist, get_storage, get_upload_dir
    from app.core.uploads import validate_batch, validate_upload

    ocr = OCRService()
    storage = get_storage(get_upload_dir())
    documents: dict[str, Any] = {}
    total_bytes = 0

    for upload, doc_type in zip(files, document_types):
        content = await upload.read()
        detected = validate_upload(content, upload.filename or doc_type)
        total_bytes += len(content)
        validate_batch(len(files), total_bytes)

        # Stored like any other submission. Without this the validation could
        # be retrieved but its pages could not be rendered, so /v1/validations
        # returned findings pointing at documents that no longer existed.
        stored_name = _persist(
            content, upload.filename or doc_type, doc_type, storage, detected
        )
        result = await run_in_threadpool(
            ocr.extract, content, upload.filename or "", doc_type
        )
        documents[doc_type] = {
            "filename": Path(upload.filename or doc_type).name,
            "stored_path": stored_name,
            "content_type": detected,
            "size_bytes": len(content),
            **result.to_dict(),
        }

    context: dict[str, Any] = {}
    if company_type:
        context["company_type"] = company_type.upper()
    if fiscal_year_end:
        context["fiscal_year_end"] = fiscal_year_end

    payload = {
        "transaction_type": transaction_type,
        "documents": documents,
        "submitted_at": submitted_at,
        "declaration": declared,
        **context,
    }

    from app.api.submissions import _parse_iso_date

    completeness = check_completeness(payload, today=_parse_iso_date(submitted_at))
    # Derived from the completeness result, never recomputed from the documents.
    # Two independent passes can disagree, and a response whose `findings`
    # contradict its own `status` is unusable to anyone integrating against it.
    flags = flags_from_result(completeness)
    serialised = completeness.to_dict()

    submission = store.create(
        transaction_type=transaction_type,
        documents=documents,
        completeness=serialised,
        flags=[flag.to_dict() for flag in flags],
        # API_VALIDATED, not SUBMITTED: an integrator asking whether a dossier
        # would be rejected has not filed anything, and a pre-validation must
        # not appear in an officer's queue as something awaiting their
        # decision.
        status="API_VALIDATED",
        submitted_at=submitted_at,
        context={**context, "declaration": declared, "via": "api", "owner": caller.owner}
        if declared
        else {**context, "via": "api", "owner": caller.owner},
    )

    await caller.record_call()

    return {
        "validation_id": submission.id,
        "transaction_type": transaction_type,
        "status": serialised["status"],
        "accepted": serialised["status"] == "COMPLETE",
        "missing_documents": serialised["missing_documents"],
        "checks": serialised["checks"],
        "skipped_checks": serialised["skipped_checks"],
        "findings": [flag.to_dict() for flag in flags],
        "summary": flag_summary(flags),
        "deadline": serialised.get("deadline"),
        "quota": {
            "monthly_quota": caller.key.monthly_quota,
            "used": caller.key.calls_this_period,
            "remaining": caller.remaining,
        },
    }


@router.get("/validations/{validation_id}", response_model=ValidationResponse)
def get_validation(
    validation_id: str,
    caller: ApiCaller = Depends(current_api_caller),
    store: SubmissionStore = Depends(get_store),
) -> dict[str, Any]:
    """A result produced earlier by this key's owner."""
    submission = store.get(validation_id)
    if submission is None:
        raise HTTPException(status_code=404, detail=f"No validation '{validation_id}'")

    # A validation belongs to the integration that produced it. Without this,
    # the id -- twelve hex characters -- would be an access grant to another
    # customer's dossier.
    context = submission.context or {}
    if context.get("via") != "api" or context.get("owner") != caller.owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cette validation appartient à un autre compte.",
        )

    payload = submission.to_dict()
    completeness = payload["completeness"]
    return {
        "validation_id": submission.id,
        "transaction_type": submission.transaction_type,
        "status": completeness["status"],
        "accepted": completeness["status"] == "COMPLETE",
        "missing_documents": completeness["missing_documents"],
        "checks": completeness["checks"],
        "skipped_checks": completeness.get("skipped_checks", []),
        "findings": payload["flags"],
        "summary": payload.get("flag_summary")
        or {"total": len(payload["flags"]), "errors": 0, "warnings": 0, "info": 0},
        "deadline": completeness.get("deadline"),
        "quota": {
            "monthly_quota": caller.key.monthly_quota,
            "used": caller.key.calls_this_period,
            "remaining": caller.remaining,
        },
    }


@router.get("/usage")
def usage(caller: ApiCaller = Depends(current_api_caller)) -> dict[str, Any]:
    """This key's consumption, for a customer's own dashboard."""
    return caller.key.to_public()
