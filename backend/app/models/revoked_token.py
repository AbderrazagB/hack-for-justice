"""Sessions that have been signed out before their token expired.

A JWT is valid until it expires, whoever holds it. Clearing the cookie on
logout removes it from the browser and nothing else: a token captured before
that -- from a shared machine, a proxy log, a screenshot of devtools -- stays
good for the rest of its life, and "sign out" quietly means "sign out here".

So logout records the token's `jti`, and every request checks it. One row per
sign-out, dropped once the token it names would have expired anyway.

A denylist on the token id rather than a version stamp on the account, because
signing out of one device should not sign you out of the others. A gov tool
should make signing out mean something, not make it a surprise.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, delete, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # The token's own id claim. Unique so a double sign-out is not an error.
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    # When the token would have expired on its own; the row is useless after.
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


async def revoke(session: AsyncSession, jti: str, expires_at: datetime) -> None:
    """Record a signed-out token, and sweep any that have since expired."""
    await session.execute(delete(RevokedToken).where(RevokedToken.expires_at < datetime.now(expires_at.tzinfo)))
    if await is_revoked(session, jti):
        return
    session.add(RevokedToken(jti=jti, expires_at=expires_at))
    await session.commit()


async def is_revoked(session: AsyncSession, jti: str) -> bool:
    if not jti:
        return False
    found = await session.execute(select(RevokedToken.id).where(RevokedToken.jti == jti))
    return found.first() is not None
