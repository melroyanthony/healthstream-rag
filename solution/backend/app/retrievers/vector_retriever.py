"""Vector semantic retriever."""

from app.core.base_embedder import BaseEmbedder
from app.core.base_vector_db import BaseVectorDB, VectorSearchResult


class VectorRetriever:
    """Semantic search via vector database."""

    def __init__(self, vector_db: BaseVectorDB, embedder: BaseEmbedder) -> None:
        self._vector_db = vector_db
        self._embedder = embedder

    def retrieve(
        self,
        query: str,
        patient_id: str,
        collection_name: str = "default",
        top_k: int = 20,
    ) -> list[VectorSearchResult]:
        """Retrieve semantically similar documents for a patient."""
        query_embedding = self._embedder.embed_query(query)
        return self._vector_db.query(
            collection_name=collection_name,
            query_embedding=query_embedding,
            patient_id=patient_id,
            top_k=top_k,
        )
