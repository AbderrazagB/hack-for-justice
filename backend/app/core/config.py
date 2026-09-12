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

    # Vision model used for document OCR. See app/services/ocr_service.py for why
    # Pixtral is preferred over Mistral's proprietary OCR product.
    pixtral_model: str = Field(
        default="pixtral-12b-2409", validation_alias="PIXTRAL_MODEL"
    )

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
