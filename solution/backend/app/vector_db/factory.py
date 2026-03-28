"""Vector database backend factory."""

from app.config import settings
from app.core.base_vector_db import BaseVectorDB


def create_vector_db() -> BaseVectorDB:
    """Create vector DB instance based on VECTOR_BACKEND env var."""
    backend = settings.vector_backend.lower()

    if backend == "chroma":
        from app.vector_db.chroma_db import ChromaVectorDB

        return ChromaVectorDB(persist_directory=settings.chroma_persist_directory)

    if backend == "s3vectors":
        from app.vector_db.s3_vectors import S3VectorsVectorDB

        return S3VectorsVectorDB(
            bucket_name=settings.s3_vectors_bucket,
            index_name=settings.s3_vectors_index,
            region=settings.aws_region,
        )

    raise ValueError(
        f"Unknown vector backend: {backend}. "
        "Supported: chroma, s3vectors"
    )
