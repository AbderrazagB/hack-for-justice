#!/usr/bin/env python
"""Issue, list or revoke an API key.

    cd backend && uv run python ../scripts/create_api_key.py issue "Banque X" contact@banque.tn
    cd backend && uv run python ../scripts/create_api_key.py issue "Pilote" a@b.tn --quota 50000
    cd backend && uv run python ../scripts/create_api_key.py list
    cd backend && uv run python ../scripts/create_api_key.py revoke sk_sahilli_AbCd1234

The secret is printed once and never stored. Only its hash is, so a lost key is
reissued rather than recovered -- which is the property that makes a leaked key
worth revoking instead of worth hiding.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from datetime import UTC, datetime

from sqlalchemy import select

from app.core.database import dispose_engine, get_sessionmaker, init_models
from app.models.api_key import (
    DEFAULT_MONTHLY_QUOTA,
    ApiKey,
    create_api_key,
    hash_key,
)


async def issue(name: str, owner: str, quota: int) -> int:
    async with get_sessionmaker()() as session:
        record, secret = await create_api_key(
            session, name=name, owner=owner, monthly_quota=quota
        )

    print(f"\n  Clé créée pour {record.owner} — « {record.name} »")
    print(f"  Quota : {record.monthly_quota} appels par mois\n")
    print(f"    {secret}\n")
    print("  Elle n'est affichée qu'une fois. Copiez-la maintenant.")
    print("  Utilisation :")
    print(f'    curl -H "Authorization: Bearer {secret}" \\')
    print("         http://localhost:8000/v1/transactions")
    return 0


async def show_all() -> int:
    async with get_sessionmaker()() as session:
        rows = (await session.execute(select(ApiKey))).scalars().all()

    if not rows:
        print("  Aucune clé émise.")
        return 0

    print(f"  {'PRÉFIXE':<22} {'PROPRIÉTAIRE':<28} {'APPELS':>12}  ÉTAT")
    for key in rows:
        state = "révoquée" if not key.active else "active"
        used = f"{key.calls_this_period}/{key.monthly_quota}"
        print(f"  {key.key_prefix + '…':<22} {key.owner:<28} {used:>12}  {state}")
    return 0


async def revoke(secret: str) -> int:
    async with get_sessionmaker()() as session:
        found = await session.execute(
            select(ApiKey).where(ApiKey.key_hash == hash_key(secret))
        )
        record = found.scalar_one_or_none()
        if record is None:
            print("  Clé inconnue.", file=sys.stderr)
            return 1
        if not record.active:
            print("  Déjà révoquée.")
            return 0
        record.revoked_at = datetime.now(UTC)
        await session.commit()
        print(f"  Révoquée : {record.key_prefix}… ({record.owner})")
    return 0


async def main() -> int:
    await init_models()
    try:
        command = sys.argv[1] if len(sys.argv) > 1 else ""
        if command == "issue" and len(sys.argv) >= 4:
            quota = DEFAULT_MONTHLY_QUOTA
            if "--quota" in sys.argv:
                quota = int(sys.argv[sys.argv.index("--quota") + 1])
            return await issue(sys.argv[2], sys.argv[3], quota)
        if command == "list":
            return await show_all()
        if command == "revoke" and len(sys.argv) >= 3:
            return await revoke(sys.argv[2])
        print(__doc__)
        return 2
    finally:
        await dispose_engine()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
