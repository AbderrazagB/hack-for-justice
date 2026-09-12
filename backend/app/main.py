"""Sahilli API.

Pre-validation and institutional review for RNE filings.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import assistant, health, query, submissions, upload

app = FastAPI(
    title="Sahilli API",
    version="0.1.0",
    description=(
        "Pre-validation and institutional review for Tunisia's National Business "
        "Registry (RNE). Sahilli validates a filing before it reaches the "
        "registry; it does not replace RNE's filing portal."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(query.router)
app.include_router(upload.router)
app.include_router(submissions.router)
app.include_router(assistant.router)
