"""Tests for health check endpoint."""


def test_health_check_returns_200(client):
    """Should return healthy status with dependency info."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"
    assert data["vector_backend"] == "chroma"


def test_health_check_includes_dependencies(client):
    """Should include dependency status in response."""
    response = client.get("/health")
    data = response.json()
    assert "dependencies" in data
    deps = data["dependencies"]
    assert deps["vector_store"] == "ok"
    assert deps["llm"] == "ok"
    assert deps["embedder"] == "ok"
