from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import AwareDatetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.admins.service import AdminService
from app.auth.constants import Portal
from app.auth.dependencies import AuthContext, get_current_auth_context, require_portal
from app.citizens.dependencies import CitizenContext, get_current_citizen
from app.core.exceptions import HealthLinkError
from app.db.session import get_db
from app.diagnostics.catalog import TEST_CATALOG
from app.diagnostics.pdf_screening import MAX_PDF_BYTES
from app.diagnostics.session_models import LabSession, LabSessionStatus
from app.diagnostics.session_schemas import AcceptLabSession, CloseLabSession, CreateLabSession, LabSessionView, LabStep, PdfVersion
from app.diagnostics.session_service import ACTIVE, LabSessionService, effective_status
from app.professionals.constants import ProfessionalRoleCode
from app.professionals.dependencies import ProfessionalAuthContext, require_verified_professional_role


router = APIRouter(tags=["lab-sessions"])
Database = Annotated[Session, Depends(get_db)]
Auth = Annotated[AuthContext, Depends(get_current_auth_context)]
Citizen = Annotated[CitizenContext, Depends(get_current_citizen)]
Lab = Annotated[ProfessionalAuthContext, Depends(require_verified_professional_role(ProfessionalRoleCode.LAB_TECHNICIAN))]
Admin = Annotated[AuthContext, Depends(require_portal(Portal.ADMIN))]
Page = Annotated[int, Query(ge=1, le=10000)]


@router.get("/diagnostics/test-catalog")
def catalog(auth: Auth):
    return [{"code": code, "name": name, "aliases": aliases} for code, (name, aliases) in TEST_CATALOG.items()]


@router.get("/citizens/me/diagnostic-sessions", response_model=list[LabSessionView])
def citizen_sessions(citizen: Citizen, db: Database, page: Page = 1):
    return LabSessionService(db).list(citizen.profile.id, page, citizen=True)


@router.post("/citizens/me/diagnostic-sessions", response_model=LabSessionView, status_code=201)
def create_session(payload: CreateLabSession, citizen: Citizen, db: Database):
    return LabSessionService(db).create(citizen.profile.id, payload, citizen.auth)


@router.post("/citizens/me/diagnostic-sessions/{session_id}/cancel", response_model=LabSessionView)
def cancel_session(session_id: UUID, citizen: Citizen, db: Database):
    return LabSessionService(db).cancel(citizen.profile.id, session_id, citizen.auth)


@router.get("/professionals/me/diagnostic-sessions", response_model=list[LabSessionView])
def lab_sessions(actor: Lab, db: Database, page: Page = 1):
    service = LabSessionService(db)
    facility = service._facility(actor.role_registration)
    return service.list(actor.role_registration.id, page, citizen=False, facility_id=facility.id)


@router.post("/professionals/me/diagnostic-sessions/accept", response_model=LabSessionView)
def accept_session(payload: AcceptLabSession, actor: Lab, db: Database):
    return LabSessionService(db).accept(actor.role_registration, payload, actor.auth)


@router.post("/professionals/me/diagnostic-sessions/{session_id}/steps/{target}", response_model=LabSessionView)
def progress(session_id: UUID, target: LabSessionStatus, actor: Lab, db: Database, payload: LabStep | None = None):
    return LabSessionService(db).transition(session_id, actor.role_registration, target, actor.auth, payload.tested_at if payload else None)


@router.post("/professionals/me/diagnostic-sessions/{session_id}/close", response_model=LabSessionView)
def close_session(session_id: UUID, payload: CloseLabSession, actor: Lab, db: Database):
    return LabSessionService(db).close(session_id, payload.reason, actor.auth, actor=actor.role_registration)


def require_recovery_access(request: Request, auth: AuthContext, db: Session) -> None:
    admin = AdminService(db, request.app.state.settings).require_active_admin(auth.user.id)
    if not admin.is_super_admin:
        raise HealthLinkError("Administrator recovery access is required.", status_code=403)


@router.get("/admin/facilities/{facility_id}/diagnostic-sessions")
def recovery_sessions(facility_id: UUID, request: Request, auth: Admin, db: Database, page: Page = 1):
    require_recovery_access(request, auth, db)
    now = datetime.now(UTC)
    rows = db.scalars(select(LabSession).where(
        LabSession.facility_id == facility_id, LabSession.status.in_(ACTIVE),
        (LabSession.status != LabSessionStatus.ACCEPTED) | (LabSession.attendance_deadline > now),
    ).order_by(LabSession.created_at.desc(), LabSession.id.desc()).offset((page - 1) * 20).limit(21)).all()
    return {"sessions": [{"id": item.id, "status": effective_status(item, now), "created_at": item.created_at}
                         for item in rows[:20]], "has_next": len(rows) > 20}


@router.post("/admin/facilities/{facility_id}/diagnostic-sessions/{session_id}/close", status_code=204)
def recover_session(facility_id: UUID, session_id: UUID, payload: CloseLabSession, request: Request, auth: Admin, db: Database):
    require_recovery_access(request, auth, db)
    LabSessionService(db).close(session_id, payload.reason, auth, facility_id=facility_id)
    return Response(status_code=204)


@router.put("/professionals/me/diagnostic-sessions/{session_id}/pdf", response_model=LabSessionView)
async def stage_pdf(session_id: UUID, request: Request, actor: Lab, db: Database,
                    catalog_code: Annotated[str | None, Query(max_length=40)] = None,
                    tested_at: AwareDatetime | None = None):
    if request.headers.get("content-type") != "application/pdf":
        raise HealthLinkError("Choose a PDF report.", status_code=415)
    buffer = bytearray()
    async for chunk in request.stream():
        if len(buffer) + len(chunk) > MAX_PDF_BYTES:
            raise HealthLinkError("The PDF must be 3 MB or smaller.", status_code=413)
        buffer.extend(chunk)
    return await run_in_threadpool(
        LabSessionService(db).stage_pdf, session_id, actor.role_registration, bytes(buffer),
        request.app.state.settings, catalog_code, tested_at, actor.auth,
    )


@router.post("/professionals/me/diagnostic-sessions/{session_id}/publish", response_model=LabSessionView)
def publish(session_id: UUID, payload: PdfVersion, actor: Lab, db: Database):
    return LabSessionService(db).publish(session_id, payload.version, actor.role_registration, actor.auth)


@router.post("/professionals/me/diagnostic-sessions/{session_id}/withdraw", response_model=LabSessionView)
def withdraw(session_id: UUID, payload: PdfVersion, actor: Lab, db: Database):
    return LabSessionService(db).withdraw(session_id, payload.version, actor.role_registration, actor.auth)


def pdf_response(content: bytes) -> Response:
    return Response(content, media_type="application/pdf", headers={
        "Content-Disposition": 'inline; filename="diagnostic-report.pdf"',
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
    })


@router.get("/diagnostic-sessions/{session_id}/pdf")
def read_pdf(session_id: UUID, auth: Auth, db: Database):
    return pdf_response(LabSessionService(db).read_pdf(session_id, auth))


@router.get("/professionals/me/diagnostic-sessions/{session_id}/pdf/{version}")
def lab_pdf(session_id: UUID, version: int, actor: Lab, db: Database):
    return pdf_response(LabSessionService(db).read_lab_pdf(session_id, version, actor.role_registration, actor.auth))
