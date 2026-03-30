"""Tests for RAG query endpoint."""

AUTH = {"Authorization": "Bearer test-patient"}


def test_query_with_no_data_returns_response(client):
    """Should return a response even with no ingested data."""
    response = client.post(
        "/api/v1/query",
        headers=AUTH,
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
    client.post(
        "/api/v1/ingest",
        headers=AUTH,
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
        headers=AUTH,
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
        headers=AUTH,
        json={"question": ""},
    )
    assert response.status_code == 422


def test_query_includes_metadata(client):
    """Should include pipeline metadata in response."""
    response = client.post(
        "/api/v1/query",
        headers=AUTH,
        json={"question": "What is my AHI?"},
    )
    data = response.json()
    assert "metadata" in data
    assert "model" in data["metadata"]
    assert "latency_ms" in data["metadata"]


def test_query_deduplicates_citations_by_source_id(client):
    """Should return each source_id at most once even when ingested multiple times."""
    for _ in range(2):
        client.post(
            "/api/v1/ingest",
            headers=AUTH,
            json={
                "documents": [
                    {
                        "text": "Sleep session: myAir score 88, AHI 2.1",
                        "source_type": "healthkit",
                        "source_id": "dup-session-001",
                    },
                ],
            },
        )

    response = client.post(
        "/api/v1/query",
        headers=AUTH,
        json={"question": "What was my sleep score?"},
    )
    data = response.json()
    source_ids = [c["source_id"] for c in data["citations"]]
    assert len(source_ids) == len(set(source_ids)), (
        f"Duplicate source_ids in citations: {source_ids}"
    )


def test_query_respects_patient_isolation(client):
    """Should only return data for the authenticated patient."""
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

    response = client.post(
        "/api/v1/query",
        headers={"Authorization": "Bearer patient-B"},
        json={"question": "What is my sleep score?"},
    )
    data = response.json()
    assert len(data["citations"]) == 0, (
        f"Expected 0 citations for patient-B, got {len(data['citations'])}"
    )
    assert data["metadata"]["retrieval_count"] == 0
