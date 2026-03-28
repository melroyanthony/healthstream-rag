"""RAG query endpoint."""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_query_controller
from app.api.query_controller import QueryController
from app.middleware.patient_isolation import get_patient_id
from app.models.schemas import QueryRequest, QueryResponse

router = APIRouter(prefix="/api/v1", tags=["query"])


@router.post("/query", response_model=QueryResponse)
def query_health_data(
    request: QueryRequest,
    patient_id: str = Depends(get_patient_id),
    controller: QueryController = Depends(get_query_controller),
) -> QueryResponse:
    """
    Query health data using hybrid RAG pipeline.

    Patient ID is extracted from JWT -- cross-patient access is impossible.
    """
    return controller.query(
        question=request.question,
        patient_id=patient_id,
        collection_name=request.collection_name,
        top_k=request.top_k,
    )
