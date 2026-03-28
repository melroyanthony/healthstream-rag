"""Shared test fixtures."""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

os.environ["VECTOR_BACKEND"] = "chroma"
os.environ["LLM_BACKEND"] = "anthropic"
os.environ["EMBEDDER_BACKEND"] = "local"
os.environ["MOCK_AUTH"] = "true"
os.environ["ANTHROPIC_API_KEY"] = ""


@pytest.fixture
def chroma_dir():
    """Temporary directory for ChromaDB data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def vector_db(chroma_dir):
    """Fresh ChromaDB instance."""
    from app.vector_db.chroma_db import ChromaVectorDB

    return ChromaVectorDB(persist_directory=chroma_dir)


@pytest.fixture(scope="session")
def embedder():
    """Session-scoped local embedder (model loaded once)."""
    from app.embedders.local_embedder import LocalEmbedder

    return LocalEmbedder()


@pytest.fixture
def client(chroma_dir):
    """FastAPI test client with fresh dependencies per test."""
    from app.api.dependencies import get_embedder, get_query_controller, get_vector_db
    from app.api.main import create_app
    from app.api.query_controller import QueryController
    from app.embedders.local_embedder import LocalEmbedder
    from app.generators.anthropic_generator import AnthropicGenerator
    from app.vector_db.chroma_db import ChromaVectorDB

    get_vector_db.cache_clear()
    get_embedder.cache_clear()
    get_query_controller.cache_clear()

    _db = ChromaVectorDB(persist_directory=chroma_dir)
    _emb = LocalEmbedder()
    _gen = AnthropicGenerator(api_key="", model="claude-haiku-4-5-20250315")
    _controller = QueryController(vector_db=_db, embedder=_emb, generator=_gen)

    app = create_app()
    app.dependency_overrides[get_vector_db] = lambda: _db
    app.dependency_overrides[get_embedder] = lambda: _emb
    app.dependency_overrides[get_query_controller] = lambda: _controller

    with TestClient(app) as tc:
        yield tc

    app.dependency_overrides.clear()
    get_vector_db.cache_clear()
    get_embedder.cache_clear()
    get_query_controller.cache_clear()
