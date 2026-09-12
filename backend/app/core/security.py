"""Password hashing and session tokens.

Hashing uses Argon2id, the current password-hashing competition winner, via
argon2-cffi. It is memory-hard, which is what makes a stolen hash expensive to
attack offline -- unlike a plain SHA family digest, which a GPU chews through.

Tokens are signed JWTs. They are handed to the browser in an httpOnly cookie so
page JavaScript cannot read them; an XSS bug then cannot exfiltrate a session.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import settings

# Defaults from argon2-cffi track the RFC 9106 recommendations; keeping them
# rather than hand-tuning means they improve when the library does.
_hasher = PasswordHasher()

SESSION_COOKIE = "sahilli_session"


class TokenError(Exception):
    """Raised when a token is missing, malformed, expired or badly signed."""


# ------------------------------------------------------------------ passwords

def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Check a password. Never raises for a wrong password -- returns False."""
    try:
        _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False
    except Exception:  # noqa: BLE001 - a corrupt hash must not 500 a login
        return False
    return True


def needs_rehash(password_hash: str) -> bool:
    """True when the stored hash predates the current Argon2 parameters."""
    try:
        return _hasher.check_needs_rehash(password_hash)
    except Exception:  # noqa: BLE001
        return False


# --------------------------------------------------------------------- tokens

def create_session_token(user_id: uuid.UUID | str, role: str) -> tuple[str, datetime]:
    """Mint a session token. Returns the token and its expiry."""
    now = datetime.now(UTC)
    expires_at = now + timedelta(hours=settings.session_ttl_hours)

    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": uuid.uuid4().hex,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_at


def decode_session_token(token: str) -> dict[str, Any]:
    """Verify and decode a token, or raise TokenError.

    Decoding pins the algorithm explicitly. Accepting whatever the token's own
    header claims is how "alg: none" forgeries get in.
    """
    if not token:
        raise TokenError("No session token supplied")

    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Session expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Invalid session token") from exc
