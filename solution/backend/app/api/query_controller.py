"""Query controller -- orchestrates the full RAG pipeline.

1. Embed query
2. Hybrid retrieval (vector + BM25)
3. Rerank top-K
4. Generate response with citations
5. Apply guardrails
6. Record session (DynamoDB audit trail)
7. Return response with disclaimer
"""

import time

from app.config import settings
from app.core.base_embedder import BaseEmbedder
from app.core.base_generator import BaseGenerator
from app.core.base_vector_db import BaseVectorDB
from app.guardrails.pipeline import apply_guardrails
from app.metadata_store.dynamo_store import DynamoMetadataStore
from app.models.schemas import Citation, QueryMetadata, QueryResponse
from app.retrievers.bm25_retriever import BM25Retriever
from app.retrievers.hybrid_retriever import HybridRetriever
from app.retrievers.reranker import SimpleReranker
from app.retrievers.vector_retriever import VectorRetriever


def _estimate_tokens(text: str) -> int:
    """Estimate token count from text (1 word ~ 1.3 tokens)."""
    return max(1, int(len(text.split()) * 1.3)) if text.strip() else 0


def _truncate_to_budget(text: str, max_tokens: int) -> str:
    """Truncate text to fit within a token budget."""
    words = text.split()
    if not words or max_tokens <= 0:
        return ""
    # Binary search for the largest prefix that fits
    lo, hi, best = 1, len(words), ""
    while lo <= hi:
        mid = (lo + hi) // 2
        candidate = " ".join(words[:mid])
        if _estimate_tokens(candidate) <= max_tokens:
            best = candidate
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def _budget_context(chunks: list[str], max_tokens: int) -> list[str]:
    """Hard-cap context tokens to prevent Bedrock timeout on large documents.

    Always includes at least one chunk (truncated if necessary) so retrieval
    is never dropped entirely for a single oversized chunk.
    """
    if not chunks or max_tokens <= 0:
        return []
    budgeted: list[str] = []
    token_count = 0
    for chunk in chunks:
        remaining = max_tokens - token_count
        if remaining <= 0:
            break
        chunk_tokens = _estimate_tokens(chunk)
        if chunk_tokens <= remaining:
            budgeted.append(chunk)
            token_count += chunk_tokens
        else:
            truncated = _truncate_to_budget(chunk, remaining)
            if truncated:
                budgeted.append(truncated)
            break
    return budgeted


class QueryController:
    """Orchestrates retrieve -> rerank -> generate -> cite -> audit."""

    def __init__(
        self,
        vector_db: BaseVectorDB,
        embedder: BaseEmbedder,
        generator: BaseGenerator,
        metadata_store: DynamoMetadataStore | None = None,
    ) -> None:
        self._vector_db = vector_db
        self._embedder = embedder
        self._generator = generator
        self._metadata_store = metadata_store

        vector_retriever = VectorRetriever(vector_db, embedder)
        if settings.bm25_enabled:
            bm25_retriever = BM25Retriever(vector_db, metadata_store=metadata_store)
        else:
            bm25_retriever = None
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

        context_chunks = _budget_context(
            [f"[{r.metadata.get('source_id', r.id)}] {r.text}" for r in reranked],
            max_tokens=settings.context_token_budget,
        )
        answer = self._generator.generate(
            system_prompt="",
            user_message=question,
            context_chunks=context_chunks,
        )

        answer, _passed = apply_guardrails(answer, context_chunks)

        # Deduplicate citations by source_id (BM25 + vector can return same doc)
        seen_sources: set[str] = set()
        citations: list[Citation] = []
        for r in reranked:
            sid = r.metadata.get("source_id", r.id)
            if sid in seen_sources:
                continue
            seen_sources.add(sid)
            citations.append(
                Citation(
                    source_id=sid,
                    source_type=r.metadata.get("source_type", "unknown"),
                    text_snippet=r.text[:200],
                    relevance_score=r.score,
                )
            )

        elapsed_ms = (time.time() - start) * 1000
        model = self._generator.model_name()

        # Record session in DynamoDB (audit trail + multi-turn context)
        if self._metadata_store:
            self._metadata_store.record_query_session(
                patient_id=patient_id,
                question=question,
                answer=answer,
                citation_count=len(citations),
                model=model,
                latency_ms=elapsed_ms,
            )

        return QueryResponse(
            answer=answer,
            citations=citations,
            disclaimer=settings.medical_disclaimer,
            metadata=QueryMetadata(
                retrieval_count=len(retrieved),
                model=model,
                latency_ms=round(elapsed_ms, 1),
            ),
        )
