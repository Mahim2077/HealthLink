from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.core.config import Settings


router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str


@router.get("/health", response_model=HealthResponse)
def health_check(request: Request) -> HealthResponse:
    """Return process health without requiring a database connection."""

    settings: Settings = request.app.state.settings
    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        environment=settings.app_env,
    )
