"""BM25 keyword retriever for medical terminology exact match.

Reads the patient's document corpus from DynamoDB (production)
or from the vector DB (local dev with ChromaDB).

Critical for medical terminology where exact match matters:
- Drug names: "metformin" vs "biguanide"
- Device IDs: "AirSense 11 S/N 12345"
- ICD-10 codes: "E11.9"
"""

import numpy as np
from rank_bm25 import BM25Okapi

from app.config import settings
from app.core.base_vector_db import BaseVectorDB, VectorSearchResult


class BM25Retriever:
    """BM25 keyword search over patient document corpus."""

    def __init__(
        self,
        vector_db: BaseVectorDB,
        metadata_store=None,
    ) -> None:
        self._vector_db = vector_db
        self._metadata_store = metadata_store

    def retrieve(
        self,
        query: str,
        patient_id: str,
        collection_name: str = "default",
        top_k: int = 20,
    ) -> list[VectorSearchResult]:
        """Retrieve documents via BM25 keyword scoring."""
        all_docs = self._load_patient_corpus(patient_id, collection_name)

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

    def _load_patient_corpus(
        self, patient_id: str, collection_name: str
    ) -> list[VectorSearchResult]:
        """Load patient's document corpus for BM25 scoring.

        Production (S3 Vectors): reads from DynamoDB patient-documents table.
        Local dev (ChromaDB): reads from vector DB directly.
        """
        # Production: use DynamoDB as the BM25 corpus store
        if (
            self._metadata_store is not None
            and self._metadata_store.is_enabled
            and settings.vector_backend == "s3vectors"
        ):
            return self._load_from_dynamo(patient_id)

        # Local dev: use vector DB list (ChromaDB supports this natively)
        return self._vector_db.list_data_point_vectors(
            collection_name=collection_name,
            patient_id=patient_id,
        )

    def _load_from_dynamo(self, patient_id: str) -> list[VectorSearchResult]:
        """Load patient corpus from DynamoDB patient-documents table."""
        items = self._metadata_store.get_patient_documents(patient_id)
        return [
            VectorSearchResult(
                id=item.get("chunk_id", ""),
                text=item.get("text_preview", ""),
                metadata={
                    "patient_id": patient_id,
                    "source_type": item.get("source_type", ""),
                    "source_id": item.get("source_id", ""),
                },
                score=0.0,
            )
            for item in items
        ]
