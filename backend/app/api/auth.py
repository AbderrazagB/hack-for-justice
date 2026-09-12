"""Signup, login, session and sign-out."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.core.rate_limit import LOGIN_LIMIT, SIGNUP_LIMIT, enforce
from app.core.security import (
    SESSION_COOKIE,
    TokenError,
    create_session_token,
    decode_session_token,
)
from app.models.user import User, UserRole
from app.services.user_service import (
    EmailAlreadyRegistered,
    authenticate,
    create_user,
    get_by_id,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

# Long enough to resist a dictionary attack, short enough that people comply.
MIN_PASSWORD_LENGTH = 10


# ------------------------------------------------------------------- schemas

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=200)
    full_name: str = Field(min_length=2, max_length=120)
    company_name: str | None = Field(default=None, max_length=160)

    @field_validator("password")
    @classmethod
    def reject_trivial_password(cls, value: str) -> str:
        """Block the passwords a credential-stuffing list tries first.

        Not a strength meter -- length is doing most of the work. This only
        rules out the handful that a minimum length alone would let through.
        """
        lowered = value.lower()
        if lowered in {"password12", "motdepasse", "azertyuiop", "1234567890", "qwertyuiop"}:
            raise ValueError("Ce mot de passe est trop courant.")
        if len(set(value)) < 4:
            raise ValueError("Ce mot de passe est trop répétitif.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    company_name: str | None
    role: str
    created_at: str | None
    last_login_at: str | None


class SessionResponse(BaseModel):
    user: UserResponse
    expires_at: str


# ----------------------------------------------------------------- cookie ---

def _set_session_cookie(response: Response, token: str, max_age_seconds: int) -> None:
    """Attach the session as an httpOnly cookie.

    httpOnly keeps it out of reach of page JavaScript, so an XSS bug cannot
    read it. SameSite=lax is enough here because localhost:3000 and
    localhost:8000 are the same site for cookie purposes -- ports are not part
    of a site. Behind HTTPS, set COOKIE_SECURE=true.
    """
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=max_age_seconds,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        domain=settings.cookie_domain,
        path="/",
    )


# ------------------------------------------------------------- dependencies

async def current_user(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """Resolve the signed-in user, or 401."""
    token = request.cookies.get(SESSION_COOKIE, "")

    # Bearer is accepted too, so the API stays usable from curl and tests.
    if not token:
        header = request.headers.get("Authorization", "")
        if header.lower().startswith("bearer "):
            token = header[7:].strip()

    try:
        payload = decode_session_token(token)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = await get_by_id(session, payload.get("sub", ""))
    if user is None:
        # Token verified but the account is gone: treat as signed out.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Compte introuvable"
        )
    return user


async def optional_user(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User | None:
    """The signed-in user, or None. Never raises.

    Used where a route serves both guests and account holders -- creating a
    submission, reading one back -- so the absence of a session is a valid
    state rather than an error.
    """
    try:
        return await current_user(request, session)
    except HTTPException:
        return None


async def current_officer(
    user: Annotated[User, Depends(current_user)],
) -> User:
    """Require an officer account. Used to guard review endpoints."""
    if user.role != UserRole.OFFICER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cette action est réservée aux agents du registre.",
        )
    return user


# ------------------------------------------------------------------- routes

@router.post("/signup", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    request: SignupRequest,
    http_request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SessionResponse:
    """Register an applicant account and sign it in.

    Role is not accepted from the request. Self-registering as an officer would
    hand anyone the review dashboard, so officer accounts are created out of
    band (see scripts/create_officer.py).
    """
    enforce(http_request, "signup", SIGNUP_LIMIT)

    try:
        user = await create_user(
            session,
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            company_name=request.company_name,
            role=UserRole.APPLICANT,
        )
    except EmailAlreadyRegistered:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un compte existe déjà avec cette adresse e-mail.",
        ) from None

    token, expires_at = create_session_token(user.id, user.role)
    _set_session_cookie(response, token, settings.session_ttl_hours * 3600)

    return SessionResponse(
        user=UserResponse(**user.to_public()), expires_at=expires_at.isoformat()
    )


@router.post("/login", response_model=SessionResponse)
async def login(
    request: LoginRequest,
    http_request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SessionResponse:
    # Rate limited before the password is even checked: this is the endpoint a
    # credential-stuffing run targets.
    enforce(http_request, "login", LOGIN_LIMIT)

    user = await authenticate(
        session, email=request.email, password=request.password
    )

    if user is None:
        # One message for both a wrong password and an unknown address, so the
        # endpoint cannot be used to enumerate who has an account.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Adresse e-mail ou mot de passe incorrect.",
        )

    token, expires_at = create_session_token(user.id, user.role)
    _set_session_cookie(response, token, settings.session_ttl_hours * 3600)

    return SessionResponse(
        user=UserResponse(**user.to_public()), expires_at=expires_at.isoformat()
    )


@router.get("/me", response_model=UserResponse)
async def me(user: Annotated[User, Depends(current_user)]) -> UserResponse:
    return UserResponse(**user.to_public())


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(response: Response) -> dict[str, Any]:
    """Clear the session cookie.

    Deliberately does not require a valid session: signing out must work even
    when the token is already expired or malformed.
    """
    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
        domain=settings.cookie_domain,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
    return {"detail": "Session terminée."}
