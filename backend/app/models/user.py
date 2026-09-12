"""User account model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserRole(str, Enum):
    """Who the account belongs to.

    APPLICANT files dossiers; OFFICER reviews them in /admin. The role is set at
    signup for applicants only -- an officer account cannot be self-registered,
    because letting anyone claim reviewer rights would be the whole security
    model gone. See app/api/auth.py.
    """

    APPLICANT = "applicant"
    OFFICER = "officer"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Stored lower-cased and unique. Normalising on write means the uniqueness
    # constraint actually prevents "A@b.tn" and "a@b.tn" being two accounts.
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)

    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default=UserRole.APPLICANT.value, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def touch_login(self) -> None:
        self.last_login_at = datetime.now(UTC)

    def to_public(self) -> dict[str, Any]:
        """The shape returned to clients. Never includes the hash."""
        return {
            "id": str(self.id),
            "email": self.email,
            "full_name": self.full_name,
            "company_name": self.company_name,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": (
                self.last_login_at.isoformat() if self.last_login_at else None
            ),
        }
