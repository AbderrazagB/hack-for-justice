"""API keys, for callers that are programs rather than people.

The web app authenticates a person with a password and a session cookie. An
integrator is not a person: there is no browser, no login screen, and nothing to
expire after eight hours. They get a key.

Three decisions worth stating.

**Hashed with SHA-256, not Argon2.** Passwords need a slow hash because they
are low-entropy and guessable. A key here is 256 bits from `secrets`, so there
is nothing to guess; the only thing a slow hash would add is ~100 ms on every
single API call. The threat a password hash defends against does not exist for
a random secret.

**Shown once.** Only the hash is stored, so a lost key is reissued rather than
recovered. The visible prefix exists so a key can be named and revoked in a
dashboard without ever handling the secret.

**Quota on the key, not the account.** Billing and abuse are both per
integration: one customer's runaway retry loop should not exhaust the quota of
their own other integration, nor of anyone else.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, func, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# Recognisable in a log or a support ticket without being mistaken for a JWT.
KEY_PREFIX = "sk_sahilli_"
PREFIX_DISPLAY_CHARS = 8

# Calls per calendar month on the default plan. Deliberately generous for a
# pilot and trivially changed per key.
DEFAULT_MONTHLY_QUOTA = 1000


def generate_key() -> tuple[str, str, str]:
    """A new secret: the full key, its lookup hash, and its display prefix."""
    secret = secrets.token_urlsafe(32)
    full = f"{KEY_PREFIX}{secret}"
    return full, hash_key(full), full[: len(KEY_PREFIX) + PREFIX_DISPLAY_CHARS]


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # What the key is for, in the issuer's words: "Banque X - onboarding".
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # Who the calls are billed to and whose dossiers they create.
    owner: Mapped[str] = mapped_column(String(320), index=True, nullable=False)

    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(32), nullable=False)

    monthly_quota: Mapped[int] = mapped_column(
        Integer, default=DEFAULT_MONTHLY_QUOTA, nullable=False
    )
    # Reset when the period rolls over, so no job has to sweep them.
    calls_this_period: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    period_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    @property
    def active(self) -> bool:
        return self.revoked_at is None

    def to_public(self) -> dict[str, Any]:
        """Never includes the hash, and there is no secret left to include."""
        return {
            "id": str(self.id),
            "name": self.name,
            "owner": self.owner,
            "key_prefix": f"{self.key_prefix}…",
            "monthly_quota": self.monthly_quota,
            "calls_this_period": self.calls_this_period,
            "period_started_at": (
                self.period_started_at.isoformat() if self.period_started_at else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "revoked": not self.active,
        }


async def create_api_key(
    session: AsyncSession,
    *,
    name: str,
    owner: str,
    monthly_quota: int = DEFAULT_MONTHLY_QUOTA,
) -> tuple[ApiKey, str]:
    """Issue a key. The returned secret is the only time it exists in plaintext."""
    full, hashed, prefix = generate_key()
    record = ApiKey(
        name=name,
        owner=owner.strip().lower(),
        key_hash=hashed,
        key_prefix=prefix,
        monthly_quota=monthly_quota,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record, full


async def resolve_api_key(session: AsyncSession, presented: str) -> ApiKey | None:
    """The active key this secret belongs to, or None.

    Looks up by hash rather than comparing candidates, so the cost does not
    grow with the number of issued keys.
    """
    if not presented or not presented.startswith(KEY_PREFIX):
        return None

    found = await session.execute(
        select(ApiKey).where(ApiKey.key_hash == hash_key(presented))
    )
    record = found.scalar_one_or_none()
    return record if record and record.active else None


def roll_period_if_due(record: ApiKey, now: datetime | None = None) -> None:
    """Start a new counting period once the month has turned.

    Rolled on read rather than by a scheduled job: a quota that depends on a
    cron having run is a quota that silently stops working when the cron does.
    """
    now = now or datetime.now(UTC)
    started = record.period_started_at
    if started is None:
        record.period_started_at = now
        return
    if started.tzinfo is None:
        started = started.replace(tzinfo=UTC)
    if (now.year, now.month) != (started.year, started.month):
        record.calls_this_period = 0
        record.period_started_at = now


async def record_call(session: AsyncSession, record: ApiKey) -> None:
    record.calls_this_period += 1
    record.last_used_at = datetime.now(UTC)
    await session.commit()
