"""Authentication tests.

These run against a real Postgres database (sahilli_test), not a mock: the
things most worth checking here -- the unique constraint on email, the
case-insensitive collision, the round trip through a session cookie -- only
exist once the database is actually involved.

Skips cleanly when Postgres is unreachable, so the rest of the suite still runs.
"""

from __future__ import annotations

import asyncio
import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.database import Base, get_session
from app.core.security import SESSION_COOKIE, create_session_token, decode_session_token
from app.main import app
from app.models.user import User, UserRole  # noqa: F401 - registers the table
from app.services.user_service import create_user

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://immobilia:immobilia@localhost:5432/sahilli_test",
)


def _unique_email(prefix: str = "user") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}@entreprise.tn"


VALID_PASSWORD = "unlongmotdepasse"


def _engine():
    """A test engine with NullPool.

    TestClient runs the app on its own event loop while pytest-asyncio tests run
    on another, and an asyncpg connection belongs to the loop that opened it --
    sharing one across both raises "another operation is in progress". NullPool
    opens a fresh connection per session, on whichever loop is running.
    """
    return create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)


async def _schema(create: bool) -> None:
    engine = _engine()
    try:
        async with engine.begin() as connection:
            await connection.run_sync(
                Base.metadata.create_all if create else Base.metadata.drop_all
            )
    finally:
        await engine.dispose()


@pytest.fixture(scope="module")
def database():
    try:
        asyncio.run(_schema(create=True))
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Postgres unavailable for auth tests: {exc}")
    yield
    asyncio.run(_schema(create=False))


@pytest.fixture
def db_sessionmaker(database):
    return async_sessionmaker(_engine(), expire_on_commit=False)


@pytest.fixture
def auth_client(db_sessionmaker):
    async def override():
        async with db_sessionmaker() as session:
            yield session

    app.dependency_overrides[get_session] = override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_session, None)


def _signup(client, email=None, password=VALID_PASSWORD, **extra):
    payload = {
        "email": email or _unique_email(),
        "password": password,
        "full_name": "Amine Ben Salah",
        **extra,
    }
    return client.post("/auth/signup", json=payload)


# ------------------------------------------------------------------- signup

def test_signup_creates_an_applicant_and_signs_them_in(auth_client) -> None:
    email = _unique_email()
    response = _signup(auth_client, email=email, company_name="SARL Exemple")

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == email
    assert body["user"]["role"] == "applicant"
    assert body["user"]["company_name"] == "SARL Exemple"
    assert body["expires_at"]
    assert SESSION_COOKIE in response.cookies


def test_signup_never_returns_the_password_hash(auth_client) -> None:
    body = _signup(auth_client).json()
    assert "password" not in str(body)
    assert "hash" not in str(body).lower()


def test_email_is_stored_lowercased(auth_client) -> None:
    local = uuid.uuid4().hex[:10]
    response = _signup(auth_client, email=f"MiXeD-{local}@Entreprise.TN")
    assert response.json()["user"]["email"] == f"mixed-{local}@entreprise.tn"


def test_duplicate_email_is_rejected(auth_client) -> None:
    email = _unique_email()
    assert _signup(auth_client, email=email).status_code == 201
    assert _signup(auth_client, email=email).status_code == 409


def test_duplicate_is_rejected_regardless_of_case(auth_client) -> None:
    local = uuid.uuid4().hex[:10]
    assert _signup(auth_client, email=f"dup-{local}@entreprise.tn").status_code == 201
    assert _signup(auth_client, email=f"DUP-{local}@ENTREPRISE.TN").status_code == 409


@pytest.mark.parametrize(
    "password",
    ["court", "1234567890", "password12", "aaaaaaaaaaaa", ""],
)
def test_weak_passwords_are_rejected(auth_client, password: str) -> None:
    assert _signup(auth_client, password=password).status_code == 422


def test_invalid_email_is_rejected(auth_client) -> None:
    assert _signup(auth_client, email="pas-une-adresse").status_code == 422


def test_signup_cannot_self_assign_the_officer_role(auth_client) -> None:
    """The whole role model depends on this: /admin must not be self-grantable."""
    response = auth_client.post(
        "/auth/signup",
        json={
            "email": _unique_email("escalade"),
            "password": VALID_PASSWORD,
            "full_name": "Escalade",
            "role": "officer",
        },
    )
    assert response.status_code == 201
    assert response.json()["user"]["role"] == "applicant"


# -------------------------------------------------------------------- login

def test_login_succeeds_with_correct_credentials(auth_client) -> None:
    email = _unique_email()
    _signup(auth_client, email=email)
    auth_client.cookies.clear()

    response = auth_client.post(
        "/auth/login", json={"email": email, "password": VALID_PASSWORD}
    )
    assert response.status_code == 200
    assert response.json()["user"]["email"] == email
    assert response.json()["user"]["last_login_at"] is not None


def test_login_is_case_insensitive_on_email(auth_client) -> None:
    local = uuid.uuid4().hex[:10]
    _signup(auth_client, email=f"case-{local}@entreprise.tn")
    auth_client.cookies.clear()

    response = auth_client.post(
        "/auth/login",
        json={"email": f"CASE-{local}@Entreprise.TN", "password": VALID_PASSWORD},
    )
    assert response.status_code == 200


def test_wrong_password_is_rejected(auth_client) -> None:
    email = _unique_email()
    _signup(auth_client, email=email)
    auth_client.cookies.clear()

    response = auth_client.post(
        "/auth/login", json={"email": email, "password": "mauvaismotdepasse"}
    )
    assert response.status_code == 401


def test_unknown_and_wrong_password_give_the_same_answer(auth_client) -> None:
    """Otherwise /auth/login tells an attacker which addresses are registered."""
    email = _unique_email()
    _signup(auth_client, email=email)
    auth_client.cookies.clear()

    wrong = auth_client.post(
        "/auth/login", json={"email": email, "password": "mauvaismotdepasse"}
    )
    unknown = auth_client.post(
        "/auth/login",
        json={"email": _unique_email("absent"), "password": "mauvaismotdepasse"},
    )

    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"]


# ------------------------------------------------------------------ session

def test_me_returns_the_signed_in_user(auth_client) -> None:
    email = _unique_email()
    _signup(auth_client, email=email)

    response = auth_client.get("/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == email


def test_me_requires_a_session(auth_client) -> None:
    auth_client.cookies.clear()
    assert auth_client.get("/auth/me").status_code == 401


def test_session_cookie_is_http_only(auth_client) -> None:
    """Page JavaScript must not be able to read the session."""
    response = _signup(auth_client)
    cookie_header = response.headers.get("set-cookie", "")
    assert "httponly" in cookie_header.lower()
    assert "samesite=lax" in cookie_header.lower()


def test_bearer_token_is_accepted(auth_client) -> None:
    email = _unique_email()
    body = _signup(auth_client, email=email).json()
    token, _ = create_session_token(body["user"]["id"], "applicant")

    auth_client.cookies.clear()
    response = auth_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == email


def test_tampered_token_is_rejected(auth_client) -> None:
    _signup(auth_client)
    auth_client.cookies.clear()

    forged = create_session_token(uuid.uuid4(), "officer")[0][:-4] + "AAAA"
    response = auth_client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401


def test_token_for_a_deleted_account_is_rejected(auth_client) -> None:
    token, _ = create_session_token(uuid.uuid4(), "applicant")
    auth_client.cookies.clear()
    response = auth_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_logout_clears_the_session(auth_client) -> None:
    _signup(auth_client)
    assert auth_client.get("/auth/me").status_code == 200

    assert auth_client.post("/auth/logout").status_code == 200
    assert auth_client.get("/auth/me").status_code == 401


def test_logout_works_without_a_valid_session(auth_client) -> None:
    """Signing out must succeed even when the token is already expired."""
    auth_client.cookies.clear()
    assert auth_client.post("/auth/logout").status_code == 200


# ------------------------------------------------------------------- tokens

def test_token_carries_subject_and_role() -> None:
    user_id = uuid.uuid4()
    token, expires_at = create_session_token(user_id, "officer")
    payload = decode_session_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["role"] == "officer"
    assert payload["exp"] == int(expires_at.timestamp())


# --------------------------------------------------------------------- role

async def test_officer_accounts_are_created_out_of_band(db_sessionmaker) -> None:
    async with db_sessionmaker() as session:
        officer = await create_user(
            session,
            email=_unique_email("agent"),
            password=VALID_PASSWORD,
            full_name="Agent RNE",
            role=UserRole.OFFICER,
        )
    assert officer.role == "officer"
