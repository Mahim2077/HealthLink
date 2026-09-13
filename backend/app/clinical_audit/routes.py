from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.citizens.dependencies import CitizenContext, get_current_citizen
from app.clinical_audit.service import AuditService, AccessHistoryPage
from app.db.session import get_db

router = APIRouter(tags=["clinical-privacy"])


@router.get("/citizens/me/access-history", response_model=AccessHistoryPage)
def list_access_history(citizen: Annotated[CitizenContext, Depends(get_current_citizen)],
                        db: Annotated[Session, Depends(get_db)],
                        page: Annotated[int, Query(ge=1, le=10000)] = 1):
    return AuditService(db).list_owned(citizen.profile.id, page)
