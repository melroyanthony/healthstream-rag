"""Amazon S3 Vectors backend for production deployment."""

import logging

from app.core.base_vector_db import BaseVectorDB, VectorSearchResult

logger = logging.getLogger(__name__)


class S3VectorsVectorDB(BaseVectorDB):
    """
    S3 Vectors backend -- GA December 2025.

    2B vectors/index, ~100ms latency, ~90% cost reduction vs OpenSearch.
    Available in eu-west-1 (Ireland).

    HIPAA note: PHIRedactionParser runs BEFORE this class.
    Only de-identified embeddings reach S3 Vectors.
    patient_id in metadata is always a hash, never the raw identifier.
    """

    def __init__(
        self,
        bucket_name: str,
        index_name: str,
        region: str = "eu-west-1",
    ) -> None:
        self._bucket_name = bucket_name
        self._index_name = index_name
        self._region = region
        try:
            import boto3

            self._client = boto3.client("s3vectors", region_name=region)
        except Exception:
            logger.warning("boto3 s3vectors client not available, using mock mode")
            self._client = None

    def create_collection(self, name: str, dimension: int) -> None:
        """Create an S3 Vectors index."""
        if not self._client:
            return
        self._client.create_vector_index(
            vectorBucketName=self._bucket_name,
            indexName=f"{self._index_name}-{name}",
            dimension=dimension,
            distanceMetric="cosine",
        )

    def delete_collection(self, name: str) -> None:
        """Delete an S3 Vectors index."""
        if not self._client:
            return
        self._client.delete_vector_index(
            vectorBucketName=self._bucket_name,
            indexName=f"{self._index_name}-{name}",
        )

    def get_collections(self) -> list[str]:
        """List S3 Vectors indexes."""
        if not self._client:
            return []
        response = self._client.list_vector_indexes(
            vectorBucketName=self._bucket_name,
        )
        prefix = f"{self._index_name}-"
        return [
            idx["indexName"].removeprefix(prefix)
            for idx in response.get("indexes", [])
        ]

    def upsert_documents(
        self,
        collection_name: str,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> int:
        """Bulk upsert vectors to S3 Vectors."""
        if not self._client:
            return 0
        vectors = []
        for i, doc_id in enumerate(ids):
            meta = metadatas[i].copy()
            meta["document"] = documents[i]
            vectors.append({
                "key": doc_id,
                "data": {"float32": embeddings[i]},
                "metadata": meta,
            })
        self._client.put_vectors(
            vectorBucketName=self._bucket_name,
            indexName=f"{self._index_name}-{collection_name}",
            vectors=vectors,
        )
        return len(ids)

    def query(
        self,
        collection_name: str,
        query_embedding: list[float],
        patient_id: str,
        top_k: int = 20,
    ) -> list[VectorSearchResult]:
        """
        Query with mandatory patient_id filter.

        patient_id filter is MANDATORY.
        Cross-patient retrieval is architecturally impossible.
        """
        if not self._client:
            return []
        response = self._client.query_vectors(
            vectorBucketName=self._bucket_name,
            indexName=f"{self._index_name}-{collection_name}",
            queryVector={"float32": query_embedding},
            topK=top_k,
            filter={
                "equals": {
                    "key": "patient_id",
                    "stringValue": patient_id,
                }
            },
            includeMetadata=True,
        )
        results = []
        for hit in response.get("vectors", []):
            meta = hit.get("metadata", {})
            text = meta.pop("document", "")
            results.append(
                VectorSearchResult(
                    id=hit["key"],
                    text=text,
                    metadata=meta,
                    score=hit.get("score", 0.0),
                )
            )
        return results

    def delete_documents(self, collection_name: str, ids: list[str]) -> int:
        """Delete vectors by key."""
        if not self._client:
            return 0
        self._client.delete_vectors(
            vectorBucketName=self._bucket_name,
            indexName=f"{self._index_name}-{collection_name}",
            keys=ids,
        )
        return len(ids)

    def collection_count(self, collection_name: str) -> int:
        """Return approximate vector count."""
        if not self._client:
            return 0
        response = self._client.describe_vector_index(
            vectorBucketName=self._bucket_name,
            indexName=f"{self._index_name}-{collection_name}",
        )
        return response.get("vectorCount", 0)
