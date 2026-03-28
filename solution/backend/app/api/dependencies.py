"""FastAPI dependency injection -- singleton component instances."""

from functools import lru_cache

from app.api.query_controller import QueryController
from app.core.base_embedder import BaseEmbedder
from app.core.base_vector_db import BaseVectorDB
from app.embedders.factory import create_embedder
from app.generators.factory import create_generator
from app.vector_db.factory import create_vector_db


@lru_cache
def get_vector_db() -> BaseVectorDB:
    """Singleton vector DB instance."""
    return create_vector_db()


@lru_cache
def get_embedder() -> BaseEmbedder:
    """Singleton embedder instance."""
    return create_embedder()


@lru_cache
def get_query_controller() -> QueryController:
    """Singleton query controller with all dependencies."""
    vector_db = get_vector_db()
    embedder = get_embedder()
    generator = create_generator()
    return QueryController(
        vector_db=vector_db,
        embedder=embedder,
        generator=generator,
    )
