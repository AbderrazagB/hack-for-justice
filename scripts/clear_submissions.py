#!/usr/bin/env python
"""Empty the dossier queue.

The seeded demo cases and anything filed while testing share one queue, and
after a few rounds it is mostly noise. This clears the stored dossiers so the
dashboard shows only what you file next.

Accounts are untouched -- they live in Postgres, not here -- and so are the
uploaded pages themselves, in the bucket or under data/raw. Only the dossier
records go, which is what makes the queue unreadable.

    cd backend && uv run python ../scripts/clear_submissions.py
    cd backend && uv run python ../scripts/clear_submissions.py --yes
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from app.models.submission import get_store


def main() -> int:
    store = get_store()
    existing = store.list()

    if not existing:
        print("  La file est déjà vide.")
        return 0

    print(f"  {len(existing)} dossier(s) enregistré(s) :")
    for submission in existing[:8]:
        print(f"    {submission.id}  {submission.status:28} {submission.transaction_type}")
    if len(existing) > 8:
        print(f"    … et {len(existing) - 8} de plus")

    if "--yes" not in sys.argv:
        answer = input("\n  Tout supprimer ? [oui/N] ").strip().lower()
        if answer not in {"oui", "o", "yes", "y"}:
            print("  Annulé.")
            return 1

    store.clear()
    print(f"\n  {len(existing)} dossier(s) supprimé(s). Les comptes et les pièces sont intacts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
