"""Sahilli API.

Pre-validation and institutional review for RNE filings.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
    # Explicit origins from config, never "*": credentials are sent with every
    # request and a wildcard plus credentials is not permitted.
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,  # required for the session cookie to cross ports
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=600,
)

# Uploads are capped per file and per batch in app/core/uploads.py, but that
# happens after the body is read. This refuses an oversized request up front.
MAX_REQUEST_BYTES = 48 * 1024 * 1024


@app.middleware("http")
async def guard_request_size(request: Request, call_next):
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_REQUEST_BYTES:
        return JSONResponse(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            content={"detail": "Requête trop volumineuse."},
        )
    return await call_next(request)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Baseline response headers.

    The API serves JSON and uploaded documents, never HTML, so the strictest
    useful policy is to forbid framing and content sniffing outright. HSTS is
    only sent when the deployment says it is behind TLS -- asserting it over
    plain HTTP would pin a browser to a scheme this instance cannot serve.
    """
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Cross-Origin-Resource-Policy", "same-site")
    response.headers.setdefault(
        "Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"
    )
    if settings.cookie_secure:
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    return response

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(query.router)
app.include_router(upload.router)
app.include_router(submissions.router)
app.include_router(assistant.router)
