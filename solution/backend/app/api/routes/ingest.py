"""Document ingestion endpoints."""

import uuid

from fastapi import APIRouter, Depends

from app.api.dependencies import get_embedder, get_metadata_store, get_vector_db
from app.config import settings
from app.core.base_embedder import BaseEmbedder
from app.core.base_vector_db import BaseVectorDB

# Import loaders to trigger registration via @register_loader decorators
import app.loaders.ehr_loader  # noqa: F401
import app.loaders.fhir_loader  # noqa: F401
import app.loaders.healthkit_loader  # noqa: F401
from app.loaders.base import LOADER_REGISTRY, get_loader
from app.metadata_store.dynamo_store import DynamoMetadataStore
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
    metadata_store: DynamoMetadataStore = Depends(get_metadata_store),
) -> IngestResponse:
    """
    Ingest documents into the RAG pipeline (generic text).

    Pipeline: parse -> PHI redact -> embed -> store (vector + metadata).
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

    # Record ingestion metadata in DynamoDB (audit + incremental indexing)
    for i, chunk_id in enumerate(ids):
        metadata_store.record_ingestion(
            patient_id=patient_id,
            chunk_id=chunk_id,
            text=texts[i],
            source_type=metadatas[i]["source_type"],
            source_id=metadatas[i]["source_id"],
            collection_name=request.collection_name,
        )

    return IngestResponse(
        ingested_count=count,
        collection_name=request.collection_name,
        chunk_count=count,
    )


@router.post("/ingest/source", response_model=IngestResponse)
def ingest_from_source(
    source_type: str,
    raw_data: dict,
    patient_id: str = Depends(get_patient_id),
    vector_db: BaseVectorDB = Depends(get_vector_db),
    embedder: BaseEmbedder = Depends(get_embedder),
    metadata_store: DynamoMetadataStore = Depends(get_metadata_store),
) -> IngestResponse:
    """
    Ingest from a structured source using registered data loaders.

    Uses the Cognita-inspired loader registry to auto-select
    the appropriate parser (HealthKit, FHIR, EHR) based on source_type.

    Available loaders: {list(LOADER_REGISTRY.keys())}
    """
    loader = get_loader(source_type)
    loaded_docs = loader.load(raw_data)

    ids = []
    texts = []
    metadatas = []

    for doc in loaded_docs:
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

    if not texts:
        return IngestResponse(ingested_count=0, collection_name="default", chunk_count=0)

    embeddings = embedder.embed(texts)

    vector_db.create_collection(name="default", dimension=embedder.dimension())

    count = vector_db.upsert_documents(
        collection_name="default",
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )

    for i, chunk_id in enumerate(ids):
        metadata_store.record_ingestion(
            patient_id=patient_id,
            chunk_id=chunk_id,
            text=texts[i],
            source_type=metadatas[i]["source_type"],
            source_id=metadatas[i]["source_id"],
            collection_name="default",
        )

    return IngestResponse(
        ingested_count=count,
        collection_name="default",
        chunk_count=count,
    )


@router.get("/loaders")
def list_loaders() -> dict:
    """List registered data loaders."""
    return {
        "loaders": list(LOADER_REGISTRY.keys()),
        "count": len(LOADER_REGISTRY),
    }
