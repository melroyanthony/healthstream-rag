"""Base vector database interface - Cognita-inspired with patient isolation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class VectorSearchResult:
    """Single vector search result."""

    id: str
    text: str
    metadata: dict
    score: float = 0.0


class BaseVectorDB(ABC):
    """
    Abstract vector database interface.

    Adopts 6 of Cognita's 8 BaseVectorDB methods.
    Omits get_vector_store (LangChain coupling) and get_vector_client (impl leak).
    Adds mandatory patient_id parameter on query operations.
    """

    @abstractmethod
    def create_collection(self, name: str, dimension: int) -> None:
        """Create a new vector collection."""

    @abstractmethod
    def delete_collection(self, name: str) -> None:
        """Delete a vector collection."""

    @abstractmethod
    def get_collections(self) -> list[str]:
        """List all collection names."""

    @abstractmethod
    def upsert_documents(
        self,
        collection_name: str,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> int:
        """Upsert documents with embeddings and metadata. Returns count."""

    @abstractmethod
    def query(
        self,
        collection_name: str,
        query_embedding: list[float],
        patient_id: str,
        top_k: int = 20,
    ) -> list[VectorSearchResult]:
        """
        Query vectors filtered by patient_id.

        patient_id filter is MANDATORY. Cross-patient retrieval
        is architecturally impossible by design.
        """

    @abstractmethod
    def delete_documents(
        self, collection_name: str, ids: list[str]
    ) -> int:
        """Delete documents by ID. Returns count deleted."""

    @abstractmethod
    def collection_count(self, collection_name: str) -> int:
        """Return the number of vectors in a collection."""
