"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "HealthStream RAG"
    app_version: str = "1.0.0"
    debug: bool = False

    # Vector backend: chroma | s3vectors (opensearch planned, not yet implemented)
    vector_backend: str = "chroma"

    # LLM backend: anthropic | bedrock
    llm_backend: str = "anthropic"

    # Embedder backend: local | bedrock
    embedder_backend: str = "local"

    # ChromaDB
    chroma_persist_directory: str = "./chroma_data"
    chroma_collection_name: str = "default"

    # Embedding dimensions
    local_embedding_model: str = "all-MiniLM-L6-v2"
    local_embedding_dimension: int = 384

    # Anthropic (local dev)
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5-20251001"

    # AWS (production)
    aws_region: str = "eu-west-1"
    s3_vectors_bucket: str = "healthstream-vectors"
    s3_vectors_index: str = "healthstream"
    bedrock_llm_model: str = "eu.anthropic.claude-haiku-4-5-20251001-v1:0"
    bedrock_embedding_model: str = "amazon.titan-embed-text-v2:0"
    bedrock_embedding_dimension: int = 1024

    # Retrieval
    retrieval_top_k: int = 20
    rerank_top_k: int = 5
    bm25_enabled: bool = True

    # Guardrails
    grounding_threshold: float = 0.4
    medical_disclaimer: str = (
        "This information is from your health records. "
        "Always consult your care team."
    )

    # Security
    mock_auth: bool = False
    default_patient_id: str = "synthetic-patient-001"

    model_config = {"env_prefix": "", "env_file": ".env", "extra": "ignore"}


settings = Settings()
