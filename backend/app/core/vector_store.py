"""Qdrant wrapper for Sahilli.

Points at the EXTERNAL self-hosted Qdrant container (see README > Local AI
Infrastructure). Falls back to an in-memory instance only when QDRANT_URL is
blank, so unit tests can run without the container.
"""

from collections.abc import Sequence
from typing import Any

from qdrant_client import QdrantClient, models

from app.core.config import settings


class VectorStore:
    """Thin Qdrant wrapper with an in-memory default."""

    def __init__(self, collection_name: str = "rne_procedures") -> None:
        self.collection_name = collection_name
        self.client = (
            QdrantClient(url=settings.qdrant_url)
            if settings.qdrant_url
            else QdrantClient(location=":memory:")
        )

    def init_collection(self, vector_size: int | None = None) -> None:
        """Create the collection if absent. Defaults to BGE-M3's 1024 dims."""
        size = vector_size or settings.embedding_dim
        collections = {item.name for item in self.client.get_collections().collections}
        if self.collection_name not in collections:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=size,
                    distance=models.Distance.COSINE,
                ),
            )

    def upsert(self, points: Sequence[models.PointStruct]) -> None:
        self.client.upsert(
            collection_name=self.collection_name,
            points=list(points),
        )

    def search(self, vector: list[float], limit: int = 5) -> list[Any]:
        return list(
            self.client.query_points(
                collection_name=self.collection_name,
                query=vector,
                limit=limit,
            ).points
        )

    def count(self) -> int:
        return self.client.count(collection_name=self.collection_name).count
