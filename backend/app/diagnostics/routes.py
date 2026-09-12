from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.citizens.dependencies import CitizenContext, get_current_citizen
from app.core.exceptions import HealthLinkError
from app.db.session import get_db
from app.diagnostics.models import DiagnosticTestStatus
from app.diagnostics.schemas import DiagnosticAssignmentRequest, DiagnosticTechnicianChoice, DiagnosticTestCreateRequest, DiagnosticTestListResponse, DiagnosticTestView
from app.diagnostics.service import DiagnosticsService
from app.professionals.constants import ProfessionalRoleCode
from app.professionals.dependencies import ProfessionalAuthContext, require_verified_professional_role
from app.visits.dependencies import CurrentPatientAccess, get_current_patient_access_for_doctor


router = APIRouter(tags=["diagnostic-tests"])


@router.post("/professionals/current-patient/diagnostic-tests", response_model=DiagnosticTestView, status_code=status.HTTP_201_CREATED)
def create_diagnostic_test(payload: DiagnosticTestCreateRequest, db: Annotated[Session, Depends(get_db)], access: Annotated[CurrentPatientAccess | None, Depends(get_current_patient_access_for_doctor)], doctor: Annotated[ProfessionalAuthContext, Depends(require_verified_professional_role(ProfessionalRoleCode.DOCTOR))]) -> DiagnosticTestView:
    if access is None:
        raise HealthLinkError("No current chamber patient for the verified doctor.", status_code=404)
    return DiagnosticsService(db).create(access, doctor.role_registration, payload)


@router.get("/professionals/diagnostic-technicians", response_model=list[DiagnosticTechnicianChoice])
def list_diagnostic_technicians(db: Annotated[Session, Depends(get_db)], doctor: Annotated[ProfessionalAuthContext, Depends(require_verified_professional_role(ProfessionalRoleCode.DOCTOR))], search: Annotated[str | None, Query(max_length=100)] = None, test_id: uuid.UUID | None = None, visit_id: uuid.UUID | None = None) -> list[DiagnosticTechnicianChoice]:
    facility_id = doctor.role_registration.facility_id
    service = DiagnosticsService(db)
    if test_id is not None:
        test = service.repository.get(test_id)
        if test is None or test.requested_by_role_registration_id != doctor.role_registration.id:
            raise HealthLinkError("Diagnostic test not found.", status_code=404)
        facility_id = test.facility_id
    elif visit_id is not None:
        from app.visits.repository import VisitsRepository
        current = VisitsRepository(db).load_current_patient_for_doctor(doctor.auth.user.id)
        if current is None or current.visit is None or current.visit.id != visit_id:
            raise HealthLinkError("Current consultation not found.", status_code=404)
        facility_id = current.facility.id
    if facility_id is None:
        raise HealthLinkError("Doctor role has no facility context.", status_code=409)
    return DiagnosticsService(db).eligible_technicians(facility_id, search.strip() if search else None)


@router.get("/citizens/me/diagnostic-tests", response_model=DiagnosticTestListResponse)
def list_citizen_diagnostic_tests(db: Annotated[Session, Depends(get_db)], citizen: Annotated[CitizenContext, Depends(get_current_citizen)]) -> DiagnosticTestListResponse:
    return DiagnosticTestListResponse(tests=DiagnosticsService(db).list_citizen(citizen.profile.id))


@router.get("/professionals/me/diagnostic-tests", response_model=DiagnosticTestListResponse)
def list_professional_diagnostic_tests(db: Annotated[Session, Depends(get_db)], professional: Annotated[ProfessionalAuthContext, Depends(require_verified_professional_role(ProfessionalRoleCode.DOCTOR, ProfessionalRoleCode.LAB_TECHNICIAN))]) -> DiagnosticTestListResponse:
    return DiagnosticTestListResponse(tests=DiagnosticsService(db).list_professional(professional.role_registration))


@router.put("/professionals/me/diagnostic-tests/{test_id}/assignment", response_model=DiagnosticTestView)
def assign_diagnostic_test(test_id: uuid.UUID, payload: DiagnosticAssignmentRequest, db: Annotated[Session, Depends(get_db)], doctor: Annotated[ProfessionalAuthContext, Depends(require_verified_professional_role(ProfessionalRoleCode.DOCTOR))]) -> DiagnosticTestView:
    return DiagnosticsService(db).assign(test_id, doctor.role_registration, payload.assigned_to_role_registration_id)


@router.post("/professionals/me/diagnostic-tests/{test_id}/transitions/{target_status}", response_model=DiagnosticTestView)
def transition_diagnostic_test(test_id: uuid.UUID, target_status: DiagnosticTestStatus, db: Annotated[Session, Depends(get_db)], professional: Annotated[ProfessionalAuthContext, Depends(require_verified_professional_role(ProfessionalRoleCode.DOCTOR, ProfessionalRoleCode.LAB_TECHNICIAN))]) -> DiagnosticTestView:
    return DiagnosticsService(db).transition(test_id, professional.role_registration, target_status)
