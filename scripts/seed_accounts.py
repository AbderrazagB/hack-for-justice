#!/usr/bin/env python
"""Create the demo accounts.

Everything in Sahilli now requires a session -- filing, reading a dossier, the
officer queue -- so a demo needs accounts to sign in with. This creates one of
each role, idempotently, and prints the credentials.

These are demo credentials in a public repository. They are fine for a laptop
and a hackathon table; they are not fine anywhere reachable from the internet.
The password is deliberately obvious so nobody is tempted to believe otherwise.

    cd backend && uv run python ../scripts/seed_accounts.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from app.core.database import dispose_engine, get_sessionmaker, init_models
from app.core.security import hash_password
from app.models.user import UserRole
from app.services.user_service import (
    EmailAlreadyRegistered,
    create_user,
    get_by_email,
)

DEMO_PASSWORD = "DemoSahilli2026"

ACCOUNTS = [
    {
        "email": "pme@sahilli.tn",
        "full_name": "Amine Ben Salah",
        "company_name": "SARL Exemple Tunisie",
        "role": UserRole.APPLICANT,
        "what": "dépose et vérifie un dossier",
    },
    {
        "email": "agent@rne.tn",
        "full_name": "Agent RNE",
        "company_name": None,
        "role": UserRole.OFFICER,
        "what": "voit la file d'attente et décide",
    },
]


async def main() -> int:
    await init_models()

    async with get_sessionmaker()() as session:
        for account in ACCOUNTS:
            try:
                await create_user(
                    session,
                    email=account["email"],
                    password=DEMO_PASSWORD,
                    full_name=account["full_name"],
                    company_name=account["company_name"],
                    role=account["role"],
                )
                state = "créé"
            except EmailAlreadyRegistered:
                # An account left over from an earlier run has whatever password
                # it was given then. Printing credentials that do not work is
                # worse than not printing them, so the password is reset to the
                # one below and the role re-asserted.
                existing = await get_by_email(session, account["email"])
                existing.password_hash = hash_password(DEMO_PASSWORD)
                existing.role = account["role"].value
                await session.commit()
                state = "réinitialisé"
            print(f"  {account['email']:20} {account['role'].value:10} {state}")

    await dispose_engine()

    print("\n  Mot de passe (les deux comptes) :", DEMO_PASSWORD)
    for account in ACCOUNTS:
        print(f"  {account['email']:20} — {account['what']}")
    print("\n  Comptes de démonstration. À ne pas déployer tels quels.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
