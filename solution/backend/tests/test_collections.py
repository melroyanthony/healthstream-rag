"""Tests for collection management endpoints."""


def test_list_collections_initially_empty(client):
    """Should return empty list when no collections exist."""
    response = client.get("/api/v1/collections")
    assert response.status_code == 200
    data = response.json()
    assert "collections" in data


def test_create_collection(client):
    """Should create a new collection."""
    response = client.post(
        "/api/v1/collections",
        json={"name": "test-collection", "dimension": 384},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test-collection"
    assert data["dimension"] == 384


def test_create_duplicate_collection_returns_409(client):
    """Should reject duplicate collection names."""
    client.post(
        "/api/v1/collections",
        json={"name": "duplicate", "dimension": 384},
    )
    response = client.post(
        "/api/v1/collections",
        json={"name": "duplicate", "dimension": 384},
    )
    assert response.status_code == 409


def test_delete_collection(client):
    """Should delete an existing collection."""
    client.post(
        "/api/v1/collections",
        json={"name": "to-delete", "dimension": 384},
    )
    response = client.delete("/api/v1/collections/to-delete")
    assert response.status_code == 204


def test_delete_nonexistent_collection_returns_404(client):
    """Should return 404 for non-existent collection."""
    response = client.delete("/api/v1/collections/nonexistent")
    assert response.status_code == 404


def test_create_collection_validates_name(client):
    """Should reject invalid collection names."""
    response = client.post(
        "/api/v1/collections",
        json={"name": "INVALID NAME!", "dimension": 384},
    )
    assert response.status_code == 422
