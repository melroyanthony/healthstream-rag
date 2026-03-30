"""Tests for patient isolation -- HIPAA-critical.

Cross-patient retrieval must be architecturally impossible.
"""


def test_patient_isolation_zero_cross_retrieval(vector_db, embedder):
    """Should never return another patient's data."""
    vector_db.create_collection("test", dimension=384)

    docs_a = [
        "Patient A sleep session: sleep score 85, AHI 3.2",
        "Patient A medication: CPAP therapy prescribed",
    ]
    docs_b = [
        "Patient B sleep session: sleep score 65, AHI 8.5",
        "Patient B medication: BiPAP under evaluation",
    ]

    emb_a = embedder.embed(docs_a)
    emb_b = embedder.embed(docs_b)

    vector_db.upsert_documents(
        collection_name="test",
        ids=["a-1", "a-2"],
        embeddings=emb_a,
        documents=docs_a,
        metadatas=[
            {"patient_id": "patient-A", "source_type": "healthkit", "source_id": "a1"},
            {"patient_id": "patient-A", "source_type": "fhir", "source_id": "a2"},
        ],
    )
    vector_db.upsert_documents(
        collection_name="test",
        ids=["b-1", "b-2"],
        embeddings=emb_b,
        documents=docs_b,
        metadatas=[
            {"patient_id": "patient-B", "source_type": "healthkit", "source_id": "b1"},
            {"patient_id": "patient-B", "source_type": "fhir", "source_id": "b2"},
        ],
    )

    query_emb = embedder.embed_query("sleep score")

    results_a = vector_db.query("test", query_emb, patient_id="patient-A", top_k=10)
    results_b = vector_db.query("test", query_emb, patient_id="patient-B", top_k=10)

    assert len(results_a) > 0, "Patient A should have results"
    assert len(results_b) > 0, "Patient B should have results"

    # HIPAA-critical: zero cross-patient leakage
    leaked_b_in_a = [r for r in results_a if r.metadata["patient_id"] == "patient-B"]
    leaked_a_in_b = [r for r in results_b if r.metadata["patient_id"] == "patient-A"]

    assert len(leaked_b_in_a) == 0, "Patient B data leaked to Patient A query"
    assert len(leaked_a_in_b) == 0, "Patient A data leaked to Patient B query"


def test_nonexistent_patient_returns_empty(vector_db, embedder):
    """Should return empty results for a patient with no data."""
    vector_db.create_collection("test", dimension=384)

    docs = ["Some data for existing patient"]
    embs = embedder.embed(docs)
    vector_db.upsert_documents(
        collection_name="test",
        ids=["doc-1"],
        embeddings=embs,
        documents=docs,
        metadatas=[{"patient_id": "existing", "source_type": "healthkit", "source_id": "s1"}],
    )

    query_emb = embedder.embed_query("sleep")
    results = vector_db.query("test", query_emb, patient_id="nonexistent", top_k=10)
    assert len(results) == 0


def test_patient_id_from_mock_jwt(client):
    """Should extract patient_id from Bearer token in mock auth mode."""
    response = client.post(
        "/api/v1/query",
        json={"question": "What is my sleep score?"},
        headers={"Authorization": "Bearer synthetic-patient-001"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
