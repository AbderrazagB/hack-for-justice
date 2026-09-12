"""Account creation and authentication against Postgres."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, needs_rehash, verify_password
from app.models.user import User, UserRole


class EmailAlreadyRegistered(Exception):
    """Raised when a signup targets an address that already has an account."""


def normalise_email(email: str) -> str:
    """Lower-case and trim. Stored this way so uniqueness actually holds."""
    return email.strip().lower()


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(
        select(User).where(User.email == normalise_email(email))
    )
    return result.scalar_one_or_none()


async def get_by_id(session: AsyncSession, user_id: str | uuid.UUID) -> User | None:
    try:
        key = uuid.UUID(str(user_id))
    except (ValueError, AttributeError):
        return None
    return await session.get(User, key)


async def create_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: str,
    company_name: str | None = None,
    role: UserRole = UserRole.APPLICANT,
) -> User:
    """Register an account.

    The uniqueness check races against a concurrent signup, so the database
    constraint is the real guard: we catch IntegrityError and report the same
    error either way.
    """
    email = normalise_email(email)

    if await get_by_email(session, email) is not None:
        raise EmailAlreadyRegistered(email)

    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name.strip(),
        company_name=(company_name or "").strip() or None,
        role=role.value,
    )
    session.add(user)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise EmailAlreadyRegistered(email) from exc

    await session.refresh(user)
    return user


async def authenticate(
    session: AsyncSession, *, email: str, password: str
) -> User | None:
    """Return the user when the credentials match, else None.

    A missing account still runs a hash verification against a dummy value so
    the response time does not reveal whether an address is registered.
    """
    user = await get_by_email(session, email)

    if user is None:
        # Constant-ish work for an unknown address.
        verify_password(password, _DUMMY_HASH)
        return None

    if not verify_password(password, user.password_hash):
        return None

    # Transparently upgrade a hash whose parameters are now out of date.
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)

    user.touch_login()
    await session.commit()
    await session.refresh(user)
    return user


# A real Argon2 hash of a value nobody will submit, used to keep the timing of a
# failed lookup close to that of a wrong password.
_DUMMY_HASH = hash_password(uuid.uuid4().hex)
