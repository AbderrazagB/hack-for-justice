from collections.abc import Sequence
from typing import Any

from qdrant_client import QdrantClient, models

from app.core.config import settings


class VectorStore:
    """Thin Qdrant wrapper with an in-memory default."""

    def __init__(self, collection_name: str = "documents") -> None:
        self.collection_name = collection_name
        self.client = (
            QdrantClient(url=settings.qdrant_url)
            if settings.qdrant_url
            else QdrantClient(location=":memory:")
        )

    def init_collection(self, vector_size: int = 384) -> None:
        collections = {item.name for item in self.client.get_collections().collections}
        if self.collection_name not in collections:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,
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

