"""ChromaDB vector backend for local development."""

import chromadb

from app.core.base_vector_db import BaseVectorDB, VectorSearchResult


class ChromaVectorDB(BaseVectorDB):
    """
    ChromaDB implementation for local development.

    Zero cost, in-process, good developer experience.
    Uses cosine similarity and HNSW index.
    """

    def __init__(self, persist_directory: str = "./chroma_data") -> None:
        self._client = chromadb.PersistentClient(path=persist_directory)

    def create_collection(self, name: str, dimension: int) -> None:
        """Create a collection. ChromaDB auto-creates on first use."""
        self._client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine", "dimension": dimension},
        )

    def delete_collection(self, name: str) -> None:
        """Delete a collection by name."""
        self._client.delete_collection(name=name)

    def get_collections(self) -> list[str]:
        """List all collection names."""
        collections = self._client.list_collections()
        return [c.name for c in collections]

    def upsert_documents(
        self,
        collection_name: str,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> int:
        """Upsert documents into a ChromaDB collection."""
        collection = self._client.get_or_create_collection(name=collection_name)
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
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

        Cross-patient retrieval is impossible by design.
        """
        collection = self._client.get_or_create_collection(name=collection_name)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={"patient_id": patient_id},
            include=["documents", "metadatas", "distances"],
        )

        search_results = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                score = 1.0 - (results["distances"][0][i] if results["distances"] else 0.0)
                search_results.append(
                    VectorSearchResult(
                        id=doc_id,
                        text=results["documents"][0][i] if results["documents"] else "",
                        metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                        score=score,
                    )
                )

        return search_results

    def delete_documents(self, collection_name: str, ids: list[str]) -> int:
        """Delete documents by ID."""
        collection = self._client.get_collection(name=collection_name)
        collection.delete(ids=ids)
        return len(ids)

    def collection_count(self, collection_name: str) -> int:
        """Return vector count in collection."""
        collection = self._client.get_or_create_collection(name=collection_name)
        return collection.count()

    def list_data_point_vectors(
        self, collection_name: str, patient_id: str
    ) -> list[VectorSearchResult]:
        """List all vectors for a patient (used for BM25 corpus building)."""
        collection = self._client.get_or_create_collection(name=collection_name)
        results = collection.get(
            where={"patient_id": patient_id},
            include=["documents", "metadatas"],
        )
        return [
            VectorSearchResult(
                id=results["ids"][i],
                text=results["documents"][i] if results["documents"] else "",
                metadata=results["metadatas"][i] if results["metadatas"] else {},
                score=0.0,
            )
            for i in range(len(results["ids"]))
        ]

    def delete_data_point_vectors(
        self, collection_name: str, ids: list[str]
    ) -> int:
        """Delete specific data point vectors."""
        return self.delete_documents(collection_name, ids)
