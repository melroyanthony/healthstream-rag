"""Collection management endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_vector_db
from app.core.base_vector_db import BaseVectorDB
from app.models.schemas import Collection, CreateCollectionRequest

router = APIRouter(prefix="/api/v1", tags=["collections"])


@router.get("/collections")
def list_collections(
    vector_db: BaseVectorDB = Depends(get_vector_db),
) -> dict:
    """List all vector collections."""
    names = vector_db.get_collections()
    collections = [
        Collection(
            name=name,
            vector_count=vector_db.collection_count(name),
        )
        for name in names
    ]
    return {"collections": collections}


@router.post("/collections", status_code=201, response_model=Collection)
def create_collection(
    request: CreateCollectionRequest,
    vector_db: BaseVectorDB = Depends(get_vector_db),
) -> Collection:
    """Create a new vector collection."""
    existing = vector_db.get_collections()
    if request.name in existing:
        raise HTTPException(status_code=409, detail="Collection already exists")

    vector_db.create_collection(name=request.name, dimension=request.dimension)
    return Collection(
        name=request.name,
        vector_count=0,
        dimension=request.dimension,
        created_at=datetime.now(timezone.utc),
    )


@router.delete("/collections/{collection_name}", status_code=204)
def delete_collection(
    collection_name: str,
    vector_db: BaseVectorDB = Depends(get_vector_db),
) -> None:
    """Delete a vector collection."""
    existing = vector_db.get_collections()
    if collection_name not in existing:
        raise HTTPException(status_code=404, detail="Collection not found")

    vector_db.delete_collection(name=collection_name)
