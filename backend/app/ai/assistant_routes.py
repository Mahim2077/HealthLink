from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.ai.assistant_schemas import (
    AIChatRequest,
    AIChatResponse,
    MedicalHistorySummaryRequest,
    MedicalHistorySummaryResponse,
    SymptomGuidanceRequest,
    SymptomGuidanceResponse,
)
from app.ai.assistant_service import AIAssistantService
from app.ai.dependencies import get_ai_provider
from app.ai.providers import AIProvider
from app.auth.constants import Portal
from app.auth.dependencies import AuthContext, get_request_settings, require_portal
from app.citizens.dependencies import CitizenContext, get_current_citizen
from app.core.config import Settings
from app.db.session import get_db


router = APIRouter(prefix="/ai", tags=["ai-assistant"])


@router.post(
    "/medical-history/summary",
    response_model=MedicalHistorySummaryResponse,
)
async def summarize_own_medical_history(
    _payload: MedicalHistorySummaryRequest,
    citizen: Annotated[CitizenContext, Depends(get_current_citizen)],
    settings: Annotated[Settings, Depends(get_request_settings)],
    provider: Annotated[AIProvider, Depends(get_ai_provider)],
    db: Annotated[Session, Depends(get_db)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> MedicalHistorySummaryResponse:
    return await AIAssistantService(db, settings, provider).summarize_for_citizen(
        citizen=citizen,
        request_id=request_id,
    )


@router.post(
    "/patients/{citizen_id}/medical-history/summary",
    response_model=MedicalHistorySummaryResponse,
)
async def summarize_patient_medical_history(
    citizen_id: uuid.UUID,
    _payload: MedicalHistorySummaryRequest,
    auth: Annotated[
        AuthContext,
        Depends(require_portal(Portal.PROFESSIONAL)),
    ],
    settings: Annotated[Settings, Depends(get_request_settings)],
    provider: Annotated[AIProvider, Depends(get_ai_provider)],
    db: Annotated[Session, Depends(get_db)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> MedicalHistorySummaryResponse:
    return await AIAssistantService(
        db,
        settings,
        provider,
    ).summarize_for_professional(
        auth=auth,
        citizen_id=citizen_id,
        request_id=request_id,
    )


@router.post("/chat", response_model=AIChatResponse)
async def chat(
    payload: AIChatRequest,
    citizen: Annotated[CitizenContext, Depends(get_current_citizen)],
    settings: Annotated[Settings, Depends(get_request_settings)],
    provider: Annotated[AIProvider, Depends(get_ai_provider)],
    db: Annotated[Session, Depends(get_db)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AIChatResponse:
    return await AIAssistantService(db, settings, provider).chat(
        citizen=citizen,
        request=payload,
        request_id=request_id,
    )


@router.post("/symptom-guidance", response_model=SymptomGuidanceResponse)
async def symptom_guidance(
    payload: SymptomGuidanceRequest,
    citizen: Annotated[CitizenContext, Depends(get_current_citizen)],
    settings: Annotated[Settings, Depends(get_request_settings)],
    provider: Annotated[AIProvider, Depends(get_ai_provider)],
    db: Annotated[Session, Depends(get_db)],
) -> SymptomGuidanceResponse:
    return await AIAssistantService(db, settings, provider).symptom_guidance(
        citizen=citizen,
        request=payload,
    )


__all__ = ["router"]
