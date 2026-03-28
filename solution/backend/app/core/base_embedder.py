"""Base embedder interface."""

from abc import ABC, abstractmethod


class BaseEmbedder(ABC):
    """Abstract interface for text embedding."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts into vectors."""

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed a single query text."""

    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension."""
