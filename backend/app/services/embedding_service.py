from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """Generate sentence embeddings with all-MiniLM-L6-v2."""

    def __init__(self) -> None:
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts).tolist()

