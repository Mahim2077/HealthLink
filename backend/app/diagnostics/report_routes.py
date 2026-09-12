import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import AuthContext, get_current_auth_context
from app.citizens.dependencies import CitizenContext, get_current_citizen
from app.db.session import get_db
from app.diagnostics.report_schemas import LabReportInput, LabReportView, LabTrendPoint
from app.diagnostics.report_service import LabReportService
from app.professionals.constants import ProfessionalRoleCode
from app.professionals.dependencies import ProfessionalAuthContext, require_verified_professional_role

router = APIRouter(tags=["lab-reports"])
LabActor = Annotated[ProfessionalAuthContext, Depends(require_verified_professional_role(ProfessionalRoleCode.LAB_TECHNICIAN))]
Database = Annotated[Session, Depends(get_db)]


@router.put("/diagnostic-tests/{test_id}/lab-report", response_model=LabReportView)
def save_report(test_id: uuid.UUID, payload: LabReportInput, actor: LabActor, db: Database):
    return LabReportService(db).save(test_id, actor.role_registration, payload)


@router.post("/diagnostic-tests/{test_id}/lab-report/finalize", response_model=LabReportView)
def finalize_report(test_id: uuid.UUID, actor: LabActor, db: Database):
    return LabReportService(db).finalize(test_id, actor.role_registration)


@router.get("/diagnostic-tests/{test_id}/lab-report", response_model=LabReportView | None)
def read_report(test_id: uuid.UUID, auth: Annotated[AuthContext, Depends(get_current_auth_context)], db: Database):
    return LabReportService(db).read(test_id, auth)


@router.get("/citizens/me/lab-reports", response_model=list[LabReportView])
def list_reports(citizen: Annotated[CitizenContext, Depends(get_current_citizen)], db: Database, page: Annotated[int, Query(ge=1, le=10000)] = 1):
    return LabReportService(db).list_citizen(citizen.profile.id, page)


@router.get("/citizens/me/lab-trends", response_model=list[LabTrendPoint])
def list_trends(citizen: Annotated[CitizenContext, Depends(get_current_citizen)], db: Database, page: Annotated[int, Query(ge=1, le=10000)] = 1):
    return LabReportService(db).trends(citizen.profile.id, page)
