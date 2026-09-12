#!/usr/bin/env python
"""Create an officer account.

Officer accounts cannot be self-registered -- /auth/signup always creates an
applicant, because letting anyone claim reviewer rights would defeat the point
of having roles at all. This script is the out-of-band path.

    cd backend && uv run python ../scripts/create_officer.py agent@rne.tn "Nom Agent"
"""

from __future__ import annotations

import asyncio
import getpass
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from app.core.database import (
    dispose_engine,
    get_sessionmaker,
    init_models,
)
from app.models.user import UserRole
from app.services.user_service import (
    EmailAlreadyRegistered,
    create_user,
)

MIN_PASSWORD_LENGTH = 10


async def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2

    email, full_name = sys.argv[1], sys.argv[2]

    password = getpass.getpass("Mot de passe : ")
    if len(password) < MIN_PASSWORD_LENGTH:
        print(f"Le mot de passe doit faire au moins {MIN_PASSWORD_LENGTH} caractères.", file=sys.stderr)
        return 1
    if password != getpass.getpass("Confirmer : "):
        print("Les mots de passe ne correspondent pas.", file=sys.stderr)
        return 1

    await init_models()
    async with get_sessionmaker()() as session:
        try:
            user = await create_user(
                session,
                email=email,
                password=password,
                full_name=full_name,
                role=UserRole.OFFICER,
            )
        except EmailAlreadyRegistered:
            print(f"Un compte existe déjà pour {email}.", file=sys.stderr)
            return 1

    print(f"Compte agent créé : {user.email} ({user.id})")
    await dispose_engine()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
