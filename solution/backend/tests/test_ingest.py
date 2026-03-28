"""Tests for document ingestion endpoint."""


def test_ingest_documents(client):
    """Should ingest documents and return count."""
    response = client.post(
        "/api/v1/ingest",
        json={
            "documents": [
                {
                    "text": "Sleep session: myAir score 85, AHI 3.2 events/hour",
                    "source_type": "healthkit",
                    "source_id": "session-001",
                },
                {
                    "text": "FHIR Condition: Obstructive Sleep Apnea G47.33",
                    "source_type": "fhir",
                    "source_id": "cond-001",
                },
            ],
            "collection_name": "default",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ingested_count"] == 2
    assert data["collection_name"] == "default"


def test_ingest_validates_source_type(client):
    """Should reject invalid source types."""
    response = client.post(
        "/api/v1/ingest",
        json={
            "documents": [
                {
                    "text": "Some text",
                    "source_type": "invalid_type",
                    "source_id": "s1",
                }
            ],
        },
    )
    assert response.status_code == 422


def test_ingest_requires_documents(client):
    """Should reject empty document list."""
    response = client.post(
        "/api/v1/ingest",
        json={"documents": []},
    )
    assert response.status_code == 422
