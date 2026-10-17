from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.admins.service import AdminService
from app.auth.constants import Portal
from app.auth.dependencies import AuthContext, get_request_settings, require_portal
from app.citizens.dependencies import CitizenContext, get_current_citizen
from app.core.config import Settings
from app.dashboards.schemas import AdminOverview, CitizenOverview, ProfessionalOverview
from app.dashboards.service import DashboardService
from app.db.session import get_db
from app.professionals.constants import ProfessionalRoleCode
from app.professionals.dependencies import ProfessionalAuthContext, require_verified_professional_role

router = APIRouter(tags=["dashboards"])


@router.get("/citizens/me/overview", response_model=CitizenOverview)
def citizen_overview(citizen: Annotated[CitizenContext, Depends(get_current_citizen)], db: Annotated[Session, Depends(get_db)]):
    return DashboardService(db).citizen(citizen)


@router.get("/professionals/me/overview", response_model=ProfessionalOverview)
def professional_overview(context: Annotated[ProfessionalAuthContext, Depends(require_verified_professional_role(
    ProfessionalRoleCode.DOCTOR, ProfessionalRoleCode.LAB_TECHNICIAN))], db: Annotated[Session, Depends(get_db)]):
    return DashboardService(db).professional(context)


@router.get("/admin/overview", response_model=AdminOverview)
def admin_overview(auth: Annotated[AuthContext, Depends(require_portal(Portal.ADMIN))],
    settings: Annotated[Settings, Depends(get_request_settings)], db: Annotated[Session, Depends(get_db)]):
    AdminService(db, settings).require_active_admin(auth.user.id)
    return DashboardService(db).admin()
