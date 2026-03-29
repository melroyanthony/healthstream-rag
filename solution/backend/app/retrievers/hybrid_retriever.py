"""Hybrid retriever combining vector semantic + BM25 keyword search."""

from app.core.base_vector_db import VectorSearchResult
from app.retrievers.bm25_retriever import BM25Retriever
from app.retrievers.vector_retriever import VectorRetriever


class HybridRetriever:
    """
    Merge vector semantic and BM25 keyword results.

    Steps:
    1. Vector search: top-K semantically similar (patient-filtered)
    2. BM25 search: top-K keyword matches (patient-filtered)
    3. Merge + deduplicate by document ID
    4. Return combined unique results
    """

    def __init__(
        self,
        vector_retriever: VectorRetriever,
        bm25_retriever: BM25Retriever | None = None,
    ) -> None:
        self._vector = vector_retriever
        self._bm25 = bm25_retriever

    def retrieve(
        self,
        query: str,
        patient_id: str,
        collection_name: str = "default",
        top_k: int = 20,
    ) -> list[VectorSearchResult]:
        """Retrieve and merge results from both strategies."""
        vector_results = self._vector.retrieve(
            query=query,
            patient_id=patient_id,
            collection_name=collection_name,
            top_k=top_k,
        )

        if not self._bm25:
            return vector_results

        bm25_results = self._bm25.retrieve(
            query=query,
            patient_id=patient_id,
            collection_name=collection_name,
            top_k=top_k,
        )

        return self._merge_and_deduplicate(vector_results, bm25_results)

    @staticmethod
    def _normalize_scores(
        results: list[VectorSearchResult],
    ) -> list[VectorSearchResult]:
        """Normalize scores to 0..1 range (min-max)."""
        if not results:
            return results
        scores = [r.score for r in results]
        min_s, max_s = min(scores), max(scores)
        spread = max_s - min_s if max_s > min_s else 1.0
        for r in results:
            r.score = (r.score - min_s) / spread
        return results

    def _merge_and_deduplicate(
        self,
        vector_results: list[VectorSearchResult],
        bm25_results: list[VectorSearchResult],
    ) -> list[VectorSearchResult]:
        """Merge results, deduplicate by ID, keep highest normalized score."""
        vector_results = self._normalize_scores(vector_results)
        bm25_results = self._normalize_scores(bm25_results)

        seen: dict[str, VectorSearchResult] = {}

        def _dedup_key(r: VectorSearchResult) -> str:
            """Use source_id for dedup (same doc from multiple ingest runs)."""
            return r.metadata.get("source_id", r.id)

        for result in vector_results:
            key = _dedup_key(result)
            if key not in seen or result.score > seen[key].score:
                seen[key] = result

        for result in bm25_results:
            key = _dedup_key(result)
            if key not in seen or result.score > seen[key].score:
                seen[key] = result

        merged = list(seen.values())
        merged.sort(key=lambda r: r.score, reverse=True)
        return merged
