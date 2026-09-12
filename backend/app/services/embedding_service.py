"""Embedding client for Sahilli.

Embeddings are produced by an EXTERNAL, self-hosted HuggingFace Text Embeddings
Inference (TEI) container running BAAI/bge-m3 -- not by loading a model into this
process. Keeping the model out-of-process means the API container stays small
(no torch/transformers dependency) and the embedding server can be scaled, moved
to a GPU box, or shared with other services independently.

API SHAPE -- why POST /embed and not POST /v1/embeddings
--------------------------------------------------------
The detected container (ghcr.io/huggingface/text-embeddings-inference:86-1.8,
TEI 1.8.3) answers BOTH endpoints; we verified both return HTTP 200 against the
live container:

  * POST /embed           {"inputs": "text" | ["a","b"]}  -> [[float, ...], ...]
  * POST /v1/embeddings   {"input": ..., "model": ...}    -> {"data":[{"embedding":[...]}]}

We deliberately use the TEI-native POST /embed because it accepts a list of
strings in a single round-trip and returns a bare list of vectors, with no
OpenAI-compatibility envelope to unwrap and no `model` field to keep in sync with
whatever the server was actually launched with.
"""

from __future__ import annotations

import httpx

from app.core.config import settings


class EmbeddingServiceError(RuntimeError):
    """Raised when the external embedding container cannot be reached."""


class EmbeddingService:
    """Thin HTTP client over the external BGE-M3 (TEI) container."""

    def __init__(self, base_url: str | None = None, timeout: float = 60.0) -> None:
        self.base_url = (base_url or settings.embedding_service_url).rstrip("/")
        self.timeout = timeout

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts, returning one 1024-dim vector per input."""
        if not texts:
            return []

        try:
            response = httpx.post(
                f"{self.base_url}/embed",
                json={"inputs": texts},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise EmbeddingServiceError(
                f"Embedding service unreachable at {self.base_url}: {exc}. "
                "Is the BGE-M3 container running? See README > Local AI Infrastructure."
            ) from exc

        return response.json()

    def embed_one(self, text: str) -> list[float]:
        """Embed a single text. Convenience wrapper around `embed`."""
        return self.embed([text])[0]

    def health(self) -> bool:
        """Return True when the embedding container is reachable and ready."""
        try:
            return httpx.get(f"{self.base_url}/health", timeout=5.0).status_code == 200
        except httpx.HTTPError:
            return False
