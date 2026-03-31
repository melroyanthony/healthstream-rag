"""Tests for ChromaDB vector database backend."""


def test_create_and_list_collection(vector_db):
    """Should create a collection and list it."""
    vector_db.create_collection("test-collection", dimension=384)
    collections = vector_db.get_collections()
    assert "test-collection" in collections


def test_upsert_and_count(vector_db, embedder):
    """Should upsert documents and report correct count."""
    vector_db.create_collection("test", dimension=384)
    texts = ["Hello world", "Test document"]
    embeddings = embedder.embed(texts)

    count = vector_db.upsert_documents(
        collection_name="test",
        ids=["doc-1", "doc-2"],
        embeddings=embeddings,
        documents=texts,
        metadatas=[
            {"patient_id": "patient-A", "source_type": "healthkit", "source_id": "s1"},
            {"patient_id": "patient-A", "source_type": "fhir", "source_id": "s2"},
        ],
    )
    assert count == 2
    assert vector_db.collection_count("test") == 2


def test_query_filters_by_patient_id(vector_db, embedder):
    """Should only return documents for the queried patient."""
    vector_db.create_collection("test", dimension=384)
    texts = ["Sleep data for patient A", "Sleep data for patient B"]
    embeddings = embedder.embed(texts)

    vector_db.upsert_documents(
        collection_name="test",
        ids=["a-1", "b-1"],
        embeddings=embeddings,
        documents=texts,
        metadatas=[
            {"patient_id": "patient-A", "source_type": "healthkit", "source_id": "a1"},
            {"patient_id": "patient-B", "source_type": "healthkit", "source_id": "b1"},
        ],
    )

    query_emb = embedder.embed_query("sleep data")
    results_a = vector_db.query("test", query_emb, patient_id="patient-A", top_k=10)
    results_b = vector_db.query("test", query_emb, patient_id="patient-B", top_k=10)

    assert all(r.metadata["patient_id"] == "patient-A" for r in results_a)
    assert all(r.metadata["patient_id"] == "patient-B" for r in results_b)


def test_delete_documents(vector_db, embedder):
    """Should delete documents by ID."""
    vector_db.create_collection("test", dimension=384)
    embeddings = embedder.embed(["doc to delete"])

    vector_db.upsert_documents(
        collection_name="test",
        ids=["delete-me"],
        embeddings=embeddings,
        documents=["doc to delete"],
        metadatas=[{"patient_id": "p1", "source_type": "ehr", "source_id": "d1"}],
    )

    assert vector_db.collection_count("test") == 1
    vector_db.delete_documents("test", ["delete-me"])
    assert vector_db.collection_count("test") == 0


def test_delete_collection(vector_db):
    """Should delete a collection."""
    vector_db.create_collection("to-delete", dimension=384)
    assert "to-delete" in vector_db.get_collections()
    vector_db.delete_collection("to-delete")
    assert "to-delete" not in vector_db.get_collections()
