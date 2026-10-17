from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path
from sqlalchemy.orm import Session

from app.ai.clinical_schemas import (
    LabReportExplanationResponse,
    PrescriptionExplanationResponse,
)
from app.ai.clinical_service import ClinicalAIExplanationService
from app.ai.dependencies import get_ai_provider
from app.ai.providers import AIProvider
from app.auth.dependencies import (
    AuthContext,
    get_current_auth_context,
    get_request_settings,
)
from app.core.config import Settings
from app.db.session import get_db


router = APIRouter(prefix="/ai", tags=["ai-clinical-explanations"])


@router.post(
    "/prescriptions/{prescription_id}/explain",
    response_model=PrescriptionExplanationResponse,
    summary="Explain an authorized prescription without diagnosing",
)
async def explain_prescription(
    prescription_id: Annotated[uuid.UUID, Path(...)],
    auth: Annotated[AuthContext, Depends(get_current_auth_context)],
    settings: Annotated[Settings, Depends(get_request_settings)],
    provider: Annotated[AIProvider, Depends(get_ai_provider)],
    db: Annotated[Session, Depends(get_db)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> PrescriptionExplanationResponse:
    return await ClinicalAIExplanationService(
        db,
        settings,
        provider,
    ).explain_prescription(
        auth=auth,
        prescription_id=prescription_id,
        request_id=request_id,
    )


@router.post(
    "/lab-reports/{report_id}/explain",
    response_model=LabReportExplanationResponse,
    summary="Explain an authorized finalized diagnostic report without diagnosing",
)
async def explain_lab_report(
    report_id: Annotated[uuid.UUID, Path(...)],
    auth: Annotated[AuthContext, Depends(get_current_auth_context)],
    settings: Annotated[Settings, Depends(get_request_settings)],
    provider: Annotated[AIProvider, Depends(get_ai_provider)],
    db: Annotated[Session, Depends(get_db)],
    request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> LabReportExplanationResponse:
    return await ClinicalAIExplanationService(
        db,
        settings,
        provider,
    ).explain_lab_report(
        auth=auth,
        report_id=report_id,
        request_id=request_id,
    )


__all__ = ["router"]
