from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.ai.dependencies import get_ai_provider
from app.ai.providers import AIProvider
from app.ai.schemas import (
    AIGuidanceRequest,
    AIGuidanceResponse,
    AIStatusResponse,
)
from app.ai.service import AIGuidanceService
from app.auth.dependencies import get_request_settings
from app.citizens.dependencies import CitizenContext, get_current_citizen
from app.core.config import Settings
from app.db.session import get_db


router = APIRouter(prefix="/citizens/me/ai", tags=["citizen-ai"])


@router.get("/status", response_model=AIStatusResponse)
def get_ai_status(
    _citizen: Annotated[CitizenContext, Depends(get_current_citizen)],
    settings: Annotated[Settings, Depends(get_request_settings)],
) -> AIStatusResponse:
    return AIStatusResponse(
        enabled=settings.ai_enabled,
        record_context_enabled=(
            settings.ai_enabled and settings.ai_record_context_enabled
        ),
    )


@router.post("/guidance", response_model=AIGuidanceResponse)
async def generate_ai_guidance(
    payload: AIGuidanceRequest,
    citizen: Annotated[CitizenContext, Depends(get_current_citizen)],
    settings: Annotated[Settings, Depends(get_request_settings)],
    provider: Annotated[AIProvider, Depends(get_ai_provider)],
    db: Annotated[Session, Depends(get_db)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AIGuidanceResponse:
    return await AIGuidanceService(db, settings, provider).generate(
        citizen=citizen,
        request=payload,
        request_id=request_id,
    )


__all__ = ["router"]
