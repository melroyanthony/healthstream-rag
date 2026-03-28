"""Query controller -- orchestrates the full RAG pipeline.

1. Embed query
2. Hybrid retrieval (vector + BM25)
3. Rerank top-K
4. Generate response with citations
5. Apply guardrails
6. Return response with disclaimer
"""

import time

from app.config import settings
from app.core.base_embedder import BaseEmbedder
from app.core.base_generator import BaseGenerator
from app.core.base_vector_db import BaseVectorDB
from app.guardrails.pipeline import apply_guardrails
from app.models.schemas import Citation, QueryMetadata, QueryResponse
from app.retrievers.bm25_retriever import BM25Retriever
from app.retrievers.hybrid_retriever import HybridRetriever
from app.retrievers.reranker import SimpleReranker
from app.retrievers.vector_retriever import VectorRetriever


class QueryController:
    """Orchestrates retrieve -> rerank -> generate -> cite."""

    def __init__(
        self,
        vector_db: BaseVectorDB,
        embedder: BaseEmbedder,
        generator: BaseGenerator,
    ) -> None:
        self._vector_db = vector_db
        self._embedder = embedder
        self._generator = generator

        vector_retriever = VectorRetriever(vector_db, embedder)
        bm25_retriever = BM25Retriever(vector_db) if settings.bm25_enabled else None
        self._hybrid = HybridRetriever(vector_retriever, bm25_retriever)
        self._reranker = SimpleReranker()

    def query(
        self,
        question: str,
        patient_id: str,
        collection_name: str = "default",
        rerank_top_k: int = 5,
    ) -> QueryResponse:
        """Execute full RAG pipeline.

        Args:
            rerank_top_k: Number of results after reranking (returned to user).
                Retrieval size is controlled by settings.retrieval_top_k.
        """
        start = time.time()

        retrieved = self._hybrid.retrieve(
            query=question,
            patient_id=patient_id,
            collection_name=collection_name,
            top_k=settings.retrieval_top_k,
        )

        reranked = self._reranker.rerank(
            query=question,
            results=retrieved,
            top_k=rerank_top_k,
        )

        context_chunks = [
            f"[{r.metadata.get('source_id', r.id)}] {r.text}" for r in reranked
        ]
        answer = self._generator.generate(
            system_prompt="",
            user_message=question,
            context_chunks=context_chunks,
        )

        answer, _passed = apply_guardrails(answer, context_chunks)

        citations = [
            Citation(
                source_id=r.metadata.get("source_id", r.id),
                source_type=r.metadata.get("source_type", "unknown"),
                text_snippet=r.text[:200],
                relevance_score=r.score,
            )
            for r in reranked
        ]

        elapsed_ms = (time.time() - start) * 1000

        return QueryResponse(
            answer=answer,
            citations=citations,
            disclaimer=settings.medical_disclaimer,
            metadata=QueryMetadata(
                retrieval_count=len(retrieved),
                model=self._generator.model_name(),
                latency_ms=round(elapsed_ms, 1),
            ),
        )
