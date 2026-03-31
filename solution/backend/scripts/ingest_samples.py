"""Ingest sample synthetic health data into the vector store."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.embedders.factory import create_embedder  # noqa: E402
from app.middleware.phi_redaction import redact_phi  # noqa: E402
from app.vector_db.factory import create_vector_db  # noqa: E402


def main() -> None:
    """Load sample data and ingest into vector store."""
    data_path = Path(__file__).parent.parent / "data" / "sample_data.json"

    with open(data_path) as f:
        data = json.load(f)

    vector_db = create_vector_db()
    embedder = create_embedder()

    collection = settings.chroma_collection_name
    vector_db.create_collection(name=collection, dimension=embedder.dimension())

    total = 0
    for patient_id, patient_data in data["patients"].items():
        ids = []
        texts = []
        metadatas = []

        for doc in patient_data["documents"]:
            redacted = redact_phi(doc["text"])
            ids.append(doc["source_id"])
            texts.append(redacted)
            metadatas.append({
                "patient_id": patient_id,
                "source_type": doc["source_type"],
                "source_id": doc["source_id"],
                "chunk_index": 0,
            })

        embeddings = embedder.embed(texts)
        count = vector_db.upsert_documents(
            collection_name=collection,
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
        total += count
        print(f"Ingested {count} documents for {patient_id}")

    print(f"\nTotal ingested: {total} documents into collection '{collection}'")
    print(f"Vector backend: {settings.vector_backend}")


if __name__ == "__main__":
    main()
