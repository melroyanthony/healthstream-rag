"""Base reranker interface."""

from abc import ABC, abstractmethod

from app.core.base_vector_db import VectorSearchResult


class BaseReranker(ABC):
    """Abstract interface for search result reranking."""

    @abstractmethod
    def rerank(
        self,
        query: str,
        results: list[VectorSearchResult],
        top_k: int = 5,
    ) -> list[VectorSearchResult]:
        """Rerank search results by relevance to query."""
