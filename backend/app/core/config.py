from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for Sahilli.

    Sahilli talks to self-hosted infrastructure (Qdrant + a BGE-M3 embedding
    server) rather than managed cloud services, so that RNE could eventually run
    the whole retrieval stack on its own hardware. See README "Local AI
    Infrastructure".
    """

    mistral_api_key: str = Field(default="", validation_alias="MISTRAL_API_KEY")
    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")

    # Self-hosted Qdrant. Blank falls back to an in-memory store so the app still
    # boots for tests without the container running.
    qdrant_url: str = Field(default="", validation_alias="QDRANT_URL")

    # Self-hosted HuggingFace Text Embeddings Inference server running BAAI/bge-m3.
    embedding_service_url: str = Field(
        default="http://localhost:8090",
        validation_alias="EMBEDDING_SERVICE_URL",
    )

    # BGE-M3 emits 1024-dimensional vectors. Kept here because the Qdrant
    # collection must be created with a matching size.
    embedding_dim: int = Field(default=1024, validation_alias="EMBEDDING_DIM")

    # Open-weight (Apache-2.0) multimodal model used for document OCR. NOTE:
    # Pixtral is retired from the Mistral API -- see app/services/ocr_service.py
    # for the full rationale and the successor models.
    vision_model: str = Field(
        default="ministral-14b-2512", validation_alias="VISION_MODEL"
    )

    # Text model for the assistant's explanations. Also Apache-2.0 open-weight.
    chat_model: str = Field(
        default="ministral-8b-2512", validation_alias="CHAT_MODEL"
    )

    # ─── Accounts ────────────────────────────────────────────────────────────

    # Postgres holding user accounts.
    database_url: str = Field(
        default="postgresql+asyncpg://immobilia:immobilia@localhost:5432/sahilli",
        validation_alias="DATABASE_URL",
    )

    # Signing key for session tokens. MUST be overridden outside local dev --
    # the default is public knowledge and anyone could mint a valid token.
    # At least 32 bytes: PyJWT warns below that for HS256 (RFC 7518 §3.2).
    # Object storage for uploaded documents. Unset means the filesystem, which
    # is what a clone without MinIO gets.
    s3_endpoint_url: str = Field(default="", validation_alias="S3_ENDPOINT_URL")
    s3_access_key: str = Field(default="", validation_alias="S3_ACCESS_KEY")
    s3_secret_key: str = Field(default="", validation_alias="S3_SECRET_KEY")
    s3_bucket: str = Field(default="sahilli-documents", validation_alias="S3_BUCKET")
    s3_region: str = Field(default="us-east-1", validation_alias="S3_REGION")

    jwt_secret: str = Field(
        default="sahilli-local-development-secret-do-not-use-in-production",
        validation_alias="JWT_SECRET",
    )
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    session_ttl_hours: int = Field(default=12, validation_alias="SESSION_TTL_HOURS")

    # Cookie flags. Secure must be on wherever the site is served over HTTPS.
    cookie_secure: bool = Field(default=False, validation_alias="COOKIE_SECURE")
    cookie_domain: str | None = Field(default=None, validation_alias="COOKIE_DOMAIN")

    # Comma-separated list. Wildcards are not supported on purpose: credentials
    # are sent with every request, and "*" plus credentials is not permitted.
    cors_origins: str = Field(
        default="http://localhost:3000", validation_alias="CORS_ORIGINS"
    )

    # Only trust X-Forwarded-For when actually behind a proxy. Otherwise a
    # client could spoof the header and evade rate limiting by rotating it.
    trust_proxy_headers: bool = Field(default=False, validation_alias="TRUST_PROXY_HEADERS")

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
