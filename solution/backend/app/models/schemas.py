"""Pydantic models for API request/response validation."""

from datetime import datetime

from pydantic import BaseModel, Field


COLLECTION_NAME_PATTERN = r"^[a-z][a-z0-9_-]*$"


class QueryRequest(BaseModel):
    """RAG query request."""

    question: str = Field(..., min_length=1, max_length=2000)
    collection_name: str = Field(default="default", pattern=COLLECTION_NAME_PATTERN, max_length=100)
    top_k: int = Field(
        default=5, ge=1, le=20,
        description="Number of results after reranking (not retrieval size)",
    )


class Citation(BaseModel):
    """Source document citation."""

    source_id: str
    source_type: str
    text_snippet: str
    relevance_score: float = 0.0


class QueryMetadata(BaseModel):
    """Query pipeline metadata."""

    retrieval_count: int = 0
    model: str = ""
    latency_ms: float = 0.0


class QueryResponse(BaseModel):
    """RAG query response with citations."""

    answer: str
    citations: list[Citation]
    disclaimer: str
    metadata: QueryMetadata


class HealthDependency(BaseModel):
    """Health check dependency status."""

    vector_store: str = "ok"
    llm: str = "ok"
    embedder: str = "ok"


class HealthStatus(BaseModel):
    """Service health status."""

    status: str = "healthy"
    version: str = "1.0.0"
    vector_backend: str = "chroma"
    dependencies: HealthDependency = Field(default_factory=HealthDependency)


class Collection(BaseModel):
    """Vector collection info."""

    name: str
    vector_count: int = 0
    dimension: int = 384
    created_at: datetime | None = None


class CreateCollectionRequest(BaseModel):
    """Create collection request."""

    name: str = Field(..., min_length=1, max_length=100, pattern=COLLECTION_NAME_PATTERN)
    dimension: int = 384


class DocumentInput(BaseModel):
    """Document for ingestion."""

    text: str = Field(..., min_length=1)
    source_type: str = Field(..., pattern=r"^(healthkit|fhir|ehr)$")
    source_id: str
    metadata: dict | None = None


class IngestRequest(BaseModel):
    """Document ingestion request."""

    documents: list[DocumentInput] = Field(..., min_length=1, max_length=100)
    collection_name: str = Field(default="default", pattern=COLLECTION_NAME_PATTERN, max_length=100)


class IngestResponse(BaseModel):
    """Ingestion result."""

    ingested_count: int
    collection_name: str
    chunk_count: int = 0


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
