"""Authenticating a program rather than a person.

The app's own routes take a session cookie. These take a key in an
`Authorization: Bearer` header, which is what every HTTP client already knows
how to send and what every integrator already expects.

Quota is enforced here rather than in each route, so a route added later cannot
forget it. The count is incremented after the work succeeds: a caller should not
be billed for a request that failed on our side.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.api_key import ApiKey, resolve_api_key, roll_period_if_due

UNAUTHENTICATED = "Clé d'API absente ou invalide."


@dataclass
class ApiCaller:
    """The integration behind a request, and how to charge it."""

    key: ApiKey
    session: AsyncSession

    @property
    def owner(self) -> str:
        return self.key.owner

    @property
    def remaining(self) -> int:
        return max(0, self.key.monthly_quota - self.key.calls_this_period)

    async def record_call(self) -> None:
        from app.models.api_key import record_call

        await record_call(self.session, self.key)


def _presented(request: Request) -> str:
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    # X-API-Key is common enough in procurement checklists to be worth accepting.
    return request.headers.get("X-API-Key", "").strip()


async def current_api_caller(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> ApiCaller:
    key = await resolve_api_key(session, _presented(request))
    if key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=UNAUTHENTICATED,
            headers={"WWW-Authenticate": "Bearer"},
        )

    roll_period_if_due(key)

    if key.calls_this_period >= key.monthly_quota:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Quota mensuel atteint ({key.monthly_quota} appels). "
                "Il se réinitialise au début du mois suivant."
            ),
            headers={"Retry-After": "3600"},
        )

    return ApiCaller(key=key, session=session)
