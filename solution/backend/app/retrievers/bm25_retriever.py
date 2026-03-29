"""BM25 keyword retriever for medical terminology exact match."""

import numpy as np
from rank_bm25 import BM25Okapi

from app.core.base_vector_db import BaseVectorDB, VectorSearchResult


class BM25Retriever:
    """
    BM25 keyword search over patient document corpus.

    Critical for medical terminology where exact match matters:
    - Drug names: "metformin" vs "biguanide"
    - Device IDs: "AirSense 11 S/N 12345"
    - ICD-10 codes: "E11.9"
    """

    def __init__(self, vector_db: BaseVectorDB) -> None:
        self._vector_db = vector_db

    def retrieve(
        self,
        query: str,
        patient_id: str,
        collection_name: str = "default",
        top_k: int = 20,
    ) -> list[VectorSearchResult]:
        """Retrieve documents via BM25 keyword scoring."""
        all_docs = self._vector_db.list_data_point_vectors(
            collection_name=collection_name,
            patient_id=patient_id,
        )

        if not all_docs:
            return []

        tokenized_corpus = [doc.text.lower().split() for doc in all_docs]
        tokenized_query = query.lower().split()

        if not tokenized_corpus:
            return []

        bm25 = BM25Okapi(tokenized_corpus)
        scores = bm25.get_scores(tokenized_query)

        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                doc = all_docs[idx]
                results.append(
                    VectorSearchResult(
                        id=doc.id,
                        text=doc.text,
                        metadata=doc.metadata,
                        score=float(scores[idx]),
                    )
                )

        return results
