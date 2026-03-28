"""Local embedder using sentence-transformers for zero-cost development."""

from sentence_transformers import SentenceTransformer

from app.core.base_embedder import BaseEmbedder


class LocalEmbedder(BaseEmbedder):
    """
    sentence-transformers embedder for local development.

    Uses all-MiniLM-L6-v2 (384 dimensions) by default.
    Zero AWS cost.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model = SentenceTransformer(model_name)
        self._dimension = self._model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts."""
        embeddings = self._model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query."""
        embedding = self._model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def dimension(self) -> int:
        """Return embedding dimension (384 for MiniLM)."""
        return self._dimension
