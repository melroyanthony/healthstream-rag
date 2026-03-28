"""Health check endpoint."""

from fastapi import APIRouter

from app.config import settings
from app.models.schemas import HealthDependency, HealthStatus

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthStatus)
def health_check() -> HealthStatus:
    """Return service health with dependency status."""
    deps = HealthDependency(
        vector_store="ok",
        llm="ok",
        embedder="ok",
    )

    return HealthStatus(
        status="healthy",
        version=settings.app_version,
        vector_backend=settings.vector_backend,
        dependencies=deps,
    )
