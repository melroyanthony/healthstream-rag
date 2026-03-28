"""Tests for RAG query endpoint."""


def test_query_with_no_data_returns_response(client):
    """Should return a response even with no ingested data."""
    response = client.post(
        "/api/v1/query",
        json={"question": "What was my sleep score?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "citations" in data
    assert "disclaimer" in data
    assert data["disclaimer"] != ""


def test_query_with_data_returns_citations(client):
    """Should return citations when data is available."""
    # Ingest some data first
    client.post(
        "/api/v1/ingest",
        json={
            "documents": [
                {
                    "text": "Sleep session: myAir score 85, therapy hours 7.2, AHI 3.2",
                    "source_type": "healthkit",
                    "source_id": "session-001",
                },
            ],
        },
    )

    response = client.post(
        "/api/v1/query",
        json={"question": "What was my sleep score?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["citations"]) > 0
    assert data["metadata"]["retrieval_count"] > 0


def test_query_validates_question_length(client):
    """Should reject empty questions."""
    response = client.post(
        "/api/v1/query",
        json={"question": ""},
    )
    assert response.status_code == 422


def test_query_includes_metadata(client):
    """Should include pipeline metadata in response."""
    response = client.post(
        "/api/v1/query",
        json={"question": "What is my AHI?"},
    )
    data = response.json()
    assert "metadata" in data
    assert "model" in data["metadata"]
    assert "latency_ms" in data["metadata"]


def test_query_respects_patient_isolation(client):
    """Should only return data for the authenticated patient."""
    # Ingest data for patient-A
    client.post(
        "/api/v1/ingest",
        headers={"Authorization": "Bearer patient-A"},
        json={
            "documents": [
                {
                    "text": "Patient A specific sleep data with score 90",
                    "source_type": "healthkit",
                    "source_id": "a-session",
                },
            ],
        },
    )

    # Query as patient-B should not find patient-A data
    response = client.post(
        "/api/v1/query",
        headers={"Authorization": "Bearer patient-B"},
        json={"question": "What is my sleep score?"},
    )
    data = response.json()
    # Patient B has no data, so citations should be empty
    for citation in data["citations"]:
        assert "Patient A" not in citation["text_snippet"]
