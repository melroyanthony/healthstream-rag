"""Simple reranker for local development.

In production, this would use Bedrock Cohere Rerank.
For local dev, we use a lightweight cross-encoder simulation
based on keyword overlap scoring.
"""

from app.core.base_reranker import BaseReranker
from app.core.base_vector_db import VectorSearchResult


class SimpleReranker(BaseReranker):
    """
    Lightweight reranker for local development.

    Uses token overlap scoring as a proxy for cross-encoder reranking.
    Production would use Bedrock Cohere Rerank.
    """

    def rerank(
        self,
        query: str,
        results: list[VectorSearchResult],
        top_k: int = 5,
    ) -> list[VectorSearchResult]:
        """Rerank by keyword overlap with the query."""
        if not results:
            return []

        query_tokens = set(query.lower().split())

        scored_results = []
        for result in results:
            doc_tokens = set(result.text.lower().split())
            overlap = len(query_tokens & doc_tokens)
            total = len(query_tokens | doc_tokens)
            jaccard = overlap / total if total > 0 else 0.0
            combined_score = 0.7 * result.score + 0.3 * jaccard
            scored_results.append(
                VectorSearchResult(
                    id=result.id,
                    text=result.text,
                    metadata=result.metadata,
                    score=combined_score,
                )
            )

        scored_results.sort(key=lambda r: r.score, reverse=True)
        return scored_results[:top_k]
