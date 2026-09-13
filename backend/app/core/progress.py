"""What the server is doing, while it is still doing it.

Reading five pages through a vision model takes over a minute, and until now
the only sign of life was a button that changed its label. A caller passes an
`upload_id` it generated, the submission route reports each document as it
finishes reading it, and the caller polls for that.

Deliberately in memory and process-local. It is progress on a request this
process is already handling, so it lives exactly as long as that request does
and outlives nothing; persisting it would mean keeping state whose only reader
is a page that has since moved on.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

# Long enough that a slow read still has a reader, short enough that an
# abandoned upload does not sit in memory.
TTL_SECONDS = 900


@dataclass
class Progress:
    total: int = 0
    done: int = 0
    # The document being read right now, as a document-type key.
    current: str | None = None
    stage: str = "upload"
    updated_at: float = field(default_factory=time.monotonic)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "done": self.done,
            "current": self.current,
            "stage": self.stage,
        }


_entries: dict[str, Progress] = {}
_lock = threading.Lock()


def _evict(now: float) -> None:
    stale = [key for key, entry in _entries.items() if now - entry.updated_at > TTL_SECONDS]
    for key in stale:
        del _entries[key]


def start(upload_id: str, total: int) -> None:
    with _lock:
        now = time.monotonic()
        _evict(now)
        _entries[upload_id] = Progress(total=total, stage="reading", updated_at=now)


def reading(upload_id: str, document_type: str) -> None:
    with _lock:
        entry = _entries.get(upload_id)
        if entry is None:
            return
        entry.current = document_type
        entry.stage = "reading"
        entry.updated_at = time.monotonic()


def read(upload_id: str, document_type: str) -> None:
    with _lock:
        entry = _entries.get(upload_id)
        if entry is None:
            return
        entry.done += 1
        entry.current = document_type
        entry.updated_at = time.monotonic()


def checking(upload_id: str) -> None:
    with _lock:
        entry = _entries.get(upload_id)
        if entry is None:
            return
        entry.stage = "checking"
        entry.current = None
        entry.updated_at = time.monotonic()


def finish(upload_id: str) -> None:
    with _lock:
        entry = _entries.get(upload_id)
        if entry is None:
            return
        entry.stage = "done"
        entry.done = entry.total
        entry.current = None
        entry.updated_at = time.monotonic()


def get(upload_id: str) -> dict[str, Any] | None:
    with _lock:
        entry = _entries.get(upload_id)
        return entry.to_dict() if entry else None
