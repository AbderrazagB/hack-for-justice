"""A decision record that cannot be quietly rewritten.

An officer's decision on a filing is the part of this system with legal weight:
it says a citizen's dossier was approved, rejected, or sent back. Those
decisions are stored, like everything else, in a JSON file on disk -- and a
file on disk can be edited by anyone who reaches it, leaving no trace that the
record ever said something else.

So each decision carries the hash of the one before it. Change a note, a date,
an officer's name, or delete an entry entirely, and every hash after it stops
matching. That does not prevent tampering, and it is not meant to: it makes
tampering *visible*, and names the entry where the record stopped being true.

The chain spans every submission rather than running per-dossier. A per-dossier
chain would verify cleanly after someone deleted a whole dossier's history; a
single chain in decision order will not.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

GENESIS = "0" * 64

# The fields a link commits to. Anything not listed here can be changed without
# breaking the chain, so the list is the security boundary: it must name
# everything that carries meaning about who decided what, when.
SIGNED_FIELDS = ("submission_id", "action", "status", "note", "officer", "at")


def link_hash(previous: str, entry: dict[str, Any]) -> str:
    """The hash committing this decision to the one before it.

    Serialised with sorted keys and no incidental whitespace, so the digest
    depends on the values and not on how the JSON happened to be written.
    """
    payload = {field: entry.get(field, "") for field in SIGNED_FIELDS}
    material = previous + json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


@dataclass
class Verification:
    intact: bool
    entries: int
    # Where the chain first stops matching, if it does.
    broken_at: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "intact": self.intact,
            "entries": self.entries,
            "broken_at": self.broken_at,
        }


def decisions_in_order(submissions: list[Any]) -> list[dict[str, Any]]:
    """Every recorded decision, oldest first, with its submission attached."""
    entries: list[dict[str, Any]] = []
    for submission in submissions:
        for review in submission.reviews or []:
            entries.append({**review, "submission_id": submission.id})
    return sorted(entries, key=lambda entry: (str(entry.get("at") or ""), entry["submission_id"]))


def verify(submissions: list[Any]) -> Verification:
    """Recompute the chain and report the first link that does not match."""
    entries = decisions_in_order(submissions)
    previous = GENESIS

    for position, entry in enumerate(entries):
        stored_previous = entry.get("previous_hash")
        expected = link_hash(previous, entry)

        # A record written before the chain existed has no hash. It is not
        # evidence of tampering, but it cannot be vouched for either, so it is
        # carried forward without a claim rather than silently blessed.
        if not entry.get("hash"):
            previous = expected
            continue

        if stored_previous != previous or entry["hash"] != expected:
            return Verification(
                intact=False,
                entries=len(entries),
                broken_at={
                    "position": position,
                    "submission_id": entry["submission_id"],
                    "at": entry.get("at"),
                    "officer": entry.get("officer"),
                    "reason": (
                        "link to the previous decision does not match"
                        if stored_previous != previous
                        else "the decision's own content does not match its hash"
                    ),
                },
            )
        previous = entry["hash"]

    return Verification(intact=True, entries=len(entries))


def head(submissions: list[Any]) -> str:
    """The hash of the most recent decision, or the genesis value."""
    entries = decisions_in_order(submissions)
    for entry in reversed(entries):
        if entry.get("hash"):
            return str(entry["hash"])
    return GENESIS
