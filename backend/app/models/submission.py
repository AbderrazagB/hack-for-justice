"""Submission domain model and store.

Persistence is a JSON file under data/processed. That is deliberate for a
hackathon: it survives a backend restart (so a demo can be set up in advance and
the officer dashboard still has a queue), needs no migration step, and is
trivially inspectable when something looks wrong on stage. Swapping in Postgres
means reimplementing SubmissionStore alone -- the API layer only touches this
interface.
"""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STORE_PATH = PROJECT_ROOT / "data" / "processed" / "submissions.json"
DEFAULT_UPLOAD_DIR = PROJECT_ROOT / "data" / "raw"


class SubmissionStatus(str, Enum):
    """The tracker the MSME sees, in order."""

    SUBMITTED = "SUBMITTED"
    PRE_VALIDATED = "PRE_VALIDATED"
    UNDER_INSTITUTIONAL_REVIEW = "UNDER_INSTITUTIONAL_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NEEDS_CORRECTION = "NEEDS_CORRECTION"


class ReviewAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CORRECTION = "request_correction"


REVIEW_ACTION_STATUS = {
    ReviewAction.APPROVE: SubmissionStatus.APPROVED,
    ReviewAction.REJECT: SubmissionStatus.REJECTED,
    ReviewAction.REQUEST_CORRECTION: SubmissionStatus.NEEDS_CORRECTION,
}

TERMINAL_STATUSES = {
    SubmissionStatus.APPROVED,
    SubmissionStatus.REJECTED,
    SubmissionStatus.NEEDS_CORRECTION,
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class ReviewEvent:
    action: str
    status: str
    note: str = ""
    officer: str = "officer"
    at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "status": self.status,
            "note": self.note,
            "officer": self.officer,
            "at": self.at,
        }


@dataclass
class Submission:
    id: str
    transaction_type: str
    status: str
    created_at: str
    updated_at: str
    # document key -> {filename, stored_path, fields, engine, degraded, ...}
    documents: dict[str, Any] = field(default_factory=dict)
    completeness: dict[str, Any] = field(default_factory=dict)
    flags: list[dict[str, Any]] = field(default_factory=list)
    reviews: list[dict[str, Any]] = field(default_factory=list)
    submitted_at: str | None = None

    # -- derived ------------------------------------------------------------

    @property
    def flag_count(self) -> int:
        return len(self.flags)

    @property
    def error_flag_count(self) -> int:
        return sum(1 for flag in self.flags if flag.get("severity") == "ERROR")

    @property
    def decided_at(self) -> str | None:
        """Timestamp of the first officer decision, if any."""
        return self.reviews[0]["at"] if self.reviews else None

    def review_latency_seconds(self) -> float | None:
        """Seconds from creation to the first officer decision."""
        if not self.reviews:
            return None
        try:
            start = datetime.fromisoformat(self.created_at)
            end = datetime.fromisoformat(self.reviews[0]["at"])
        except ValueError:
            return None
        return (end - start).total_seconds()

    # -- serialisation ------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "transaction_type": self.transaction_type,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "submitted_at": self.submitted_at,
            "documents": self.documents,
            "completeness": self.completeness,
            "flags": self.flags,
            "reviews": self.reviews,
            "flag_count": self.flag_count,
            "error_flag_count": self.error_flag_count,
        }

    def to_summary(self) -> dict[str, Any]:
        """Compact shape for the officer queue list."""
        return {
            "id": self.id,
            "transaction_type": self.transaction_type,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "flag_count": self.flag_count,
            "error_flag_count": self.error_flag_count,
            "document_count": len(self.documents),
            "completeness_status": self.completeness.get("status"),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Submission:
        return cls(
            id=raw["id"],
            transaction_type=raw["transaction_type"],
            status=raw["status"],
            created_at=raw["created_at"],
            updated_at=raw["updated_at"],
            submitted_at=raw.get("submitted_at"),
            documents=raw.get("documents", {}),
            completeness=raw.get("completeness", {}),
            flags=raw.get("flags", []),
            reviews=raw.get("reviews", []),
        )


class SubmissionStore:
    """Thread-safe JSON-backed store.

    Writes go through a temp file + atomic replace so an interrupted write can
    never leave a truncated queue behind mid-demo.
    """

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path else DEFAULT_STORE_PATH
        self._lock = threading.Lock()

    # -- persistence --------------------------------------------------------

    def _read_all(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        try:
            with self.path.open(encoding="utf-8") as handle:
                return json.load(handle)
        except (json.JSONDecodeError, OSError):
            # A corrupt store must not take the API down; start clean.
            return {}

    def _write_all(self, data: dict[str, dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        with temp.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        temp.replace(self.path)

    # -- operations ---------------------------------------------------------

    def create(
        self,
        transaction_type: str,
        documents: dict[str, Any],
        completeness: dict[str, Any],
        flags: list[dict[str, Any]],
        status: str,
        submitted_at: str | None = None,
    ) -> Submission:
        submission = Submission(
            id=uuid.uuid4().hex[:12],
            transaction_type=transaction_type,
            status=status,
            created_at=_now(),
            updated_at=_now(),
            submitted_at=submitted_at,
            documents=documents,
            completeness=completeness,
            flags=flags,
        )
        with self._lock:
            data = self._read_all()
            data[submission.id] = submission.to_dict()
            self._write_all(data)
        return submission

    def get(self, submission_id: str) -> Submission | None:
        raw = self._read_all().get(submission_id)
        return Submission.from_dict(raw) if raw else None

    def list(
        self,
        status: str | None = None,
        transaction_type: str | None = None,
    ) -> list[Submission]:
        submissions = [Submission.from_dict(raw) for raw in self._read_all().values()]
        if status:
            submissions = [s for s in submissions if s.status == status]
        if transaction_type:
            submissions = [s for s in submissions if s.transaction_type == transaction_type]
        # Newest first: an officer works the top of the queue.
        return sorted(submissions, key=lambda s: s.created_at, reverse=True)

    def add_review(
        self, submission_id: str, action: ReviewAction, note: str = "", officer: str = "officer"
    ) -> Submission | None:
        new_status = REVIEW_ACTION_STATUS[action]
        event = ReviewEvent(
            action=action.value, status=new_status.value, note=note, officer=officer
        )
        with self._lock:
            data = self._read_all()
            raw = data.get(submission_id)
            if raw is None:
                return None
            raw["reviews"].append(event.to_dict())
            raw["status"] = new_status.value
            raw["updated_at"] = event.at
            data[submission_id] = raw
            self._write_all(data)
        return Submission.from_dict(raw)

    def set_status(self, submission_id: str, status: SubmissionStatus) -> Submission | None:
        with self._lock:
            data = self._read_all()
            raw = data.get(submission_id)
            if raw is None:
                return None
            raw["status"] = status.value
            raw["updated_at"] = _now()
            data[submission_id] = raw
            self._write_all(data)
        return Submission.from_dict(raw)

    def clear(self) -> None:
        with self._lock:
            self._write_all({})


_store: SubmissionStore | None = None


def get_store() -> SubmissionStore:
    """FastAPI dependency. Overridden in tests to point at a temp file."""
    global _store
    if _store is None:
        _store = SubmissionStore()
    return _store
