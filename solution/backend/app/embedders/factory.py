"""Embedder factory."""

from app.config import settings
from app.core.base_embedder import BaseEmbedder


def create_embedder() -> BaseEmbedder:
    """Create embedder based on EMBEDDER_BACKEND env var."""
    backend = settings.embedder_backend.lower()

    if backend == "local":
        from app.embedders.local_embedder import LocalEmbedder

        return LocalEmbedder(model_name=settings.local_embedding_model)

    if backend == "bedrock":
        from app.embedders.bedrock_titan import BedrockTitanEmbedder

        return BedrockTitanEmbedder(
            model_id=settings.bedrock_embedding_model,
            region=settings.aws_region,
        )

    raise ValueError(f"Unknown embedder backend: {backend}. Supported: local, bedrock")
