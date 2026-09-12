"""Sahilli API.

Pre-validation and institutional review for RNE filings.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import assistant, auth, health, query, submissions, upload
from app.core.config import settings
from app.core.database import dispose_engine, init_models

logger = logging.getLogger(__name__)

DEFAULT_JWT_SECRET = "sahilli-local-development-secret-do-not-use-in-production"


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.jwt_secret == DEFAULT_JWT_SECRET:
        logger.warning(
            "JWT_SECRET is the built-in development default. Anyone who has read "
            "this repository can mint a valid session. Set JWT_SECRET before "
            "exposing Sahilli beyond localhost."
        )

    try:
        await init_models()
    except Exception as exc:  # noqa: BLE001
        # The registry features do not need Postgres; only accounts do. A
        # database that is down should degrade sign-in, not take the API with it.
        logger.warning("Could not initialise the accounts database: %s", exc)

    yield
    await dispose_engine()


app = FastAPI(
    title="Sahilli API",
    version="0.1.0",
    description=(
        "Pre-validation and institutional review for Tunisia's National Business "
        "Registry (RNE). Sahilli validates a filing before it reaches the "
        "registry; it does not replace RNE's filing portal."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,  # required for the session cookie to cross ports
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(query.router)
app.include_router(upload.router)
app.include_router(submissions.router)
app.include_router(assistant.router)
