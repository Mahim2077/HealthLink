from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response
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
from app.ai.conversation_schemas import ConversationDetail, ConversationPage, ConversationSendRequest, ConversationSendResponse
from app.ai.conversation_service import ConversationService
from app.auth.constants import Portal
from app.auth.dependencies import AuthContext, get_request_settings, require_portal
from app.citizens.dependencies import CitizenContext, get_current_citizen
from app.core.config import Settings
from app.db.session import get_db


router = APIRouter(prefix="/ai", tags=["ai-assistant"])


@router.get("/conversations", response_model=ConversationPage)
def list_conversations(citizen: Annotated[CitizenContext, Depends(get_current_citizen)], db: Annotated[Session, Depends(get_db)], response: Response, offset: Annotated[int, Query(ge=0, le=100_000)] = 0):
    response.headers["Cache-Control"] = "private, no-store"
    return ConversationService(db).list(citizen.profile.id, offset)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: uuid.UUID, citizen: Annotated[CitizenContext, Depends(get_current_citizen)], db: Annotated[Session, Depends(get_db)], response: Response):
    response.headers["Cache-Control"] = "private, no-store"
    return ConversationService(db).detail(citizen.profile.id, conversation_id)


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: uuid.UUID, citizen: Annotated[CitizenContext, Depends(get_current_citizen)], db: Annotated[Session, Depends(get_db)]):
    ConversationService(db).remove(citizen.profile.id, conversation_id)
    return Response(status_code=204, headers={"Cache-Control": "private, no-store"})


@router.post("/conversation-messages", response_model=ConversationSendResponse)
async def send_conversation_message(payload: ConversationSendRequest, citizen: Annotated[CitizenContext, Depends(get_current_citizen)], settings: Annotated[Settings, Depends(get_request_settings)], provider: Annotated[AIProvider, Depends(get_ai_provider)], db: Annotated[Session, Depends(get_db)], response: Response, request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None):
    response.headers["Cache-Control"] = "private, no-store"
    return await ConversationService(db).send(citizen=citizen, request=payload, assistant=AIAssistantService(db, settings, provider), request_id=request_id)


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
