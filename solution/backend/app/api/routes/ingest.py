"""Document ingestion endpoint."""

import uuid

from fastapi import APIRouter, Depends

from app.api.dependencies import get_embedder, get_vector_db
from app.config import settings
from app.core.base_embedder import BaseEmbedder
from app.core.base_vector_db import BaseVectorDB
from app.middleware.patient_isolation import get_patient_id
from app.middleware.phi_redaction import redact_phi
from app.models.schemas import IngestRequest, IngestResponse

router = APIRouter(prefix="/api/v1", tags=["ingest"])


@router.post("/ingest", response_model=IngestResponse)
def ingest_documents(
    request: IngestRequest,
    patient_id: str = Depends(get_patient_id),
    vector_db: BaseVectorDB = Depends(get_vector_db),
    embedder: BaseEmbedder = Depends(get_embedder),
) -> IngestResponse:
    """
    Ingest documents into the RAG pipeline.

    Pipeline: parse -> PHI redact -> embed -> store.
    Patient ID from JWT is attached to all documents.
    """
    ids = []
    texts = []
    metadatas = []

    for doc in request.documents:
        use_comprehend = settings.embedder_backend == "bedrock"
        redacted_text = redact_phi(doc.text, use_comprehend=use_comprehend)

        chunk_id = str(uuid.uuid4())
        ids.append(chunk_id)
        texts.append(redacted_text)

        metadata = {
            "patient_id": patient_id,
            "source_type": doc.source_type,
            "source_id": doc.source_id,
            "chunk_index": 0,
        }
        if doc.metadata:
            reserved_keys = {"patient_id", "source_type", "source_id", "chunk_index"}
            safe_meta = {
                k: str(v) for k, v in doc.metadata.items()
                if k not in reserved_keys
            }
            metadata.update(safe_meta)
        metadatas.append(metadata)

    embeddings = embedder.embed(texts)

    vector_db.create_collection(
        name=request.collection_name,
        dimension=embedder.dimension(),
    )

    count = vector_db.upsert_documents(
        collection_name=request.collection_name,
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )

    return IngestResponse(
        ingested_count=count,
        collection_name=request.collection_name,
        chunk_count=count,
    )
