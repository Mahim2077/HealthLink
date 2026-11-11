from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.appointments.models import AppointmentStatus, QueueStatus, SessionStatus
from app.appointments.repository import AppointmentRepository

from app.core.exceptions import HealthLinkError
from app.citizens.models import CitizenProfile
from app.diagnostics.catalog import test_name
from app.diagnostics.models import DiagnosticTest, DiagnosticTestStatus
from app.diagnostics.session_models import DiagnosticPdf, LabSession
from app.diagnostics.repository import DiagnosticsRepository, qualifying_lab_sessions
from app.diagnostics.schemas import DiagnosticTechnicianChoice, DiagnosticTestCreateRequest, DiagnosticTestView
from app.professionals.constants import ProfessionalRoleCode
from app.professionals.models import ProfessionalRoleRegistration
from app.reminders.inbox import record_notice
from app.visits.dependencies import CurrentPatientAccess
from app.visits.models import MedicalVisit, VisitStatus
from app.facilities.models import HealthcareFacility


class DiagnosticsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = DiagnosticsRepository(db)

    def _validate_technician(self, registration_id: uuid.UUID | None, facility_id: uuid.UUID) -> None:
        facility = self.db.get(HealthcareFacility, facility_id)
        if facility is None or not facility.is_active:
            raise HealthLinkError("An active diagnostic facility is required.", status_code=422)
        if registration_id is None:
            return
        technician = self.repository.technician(registration_id)
        if technician is None:
            raise HealthLinkError("A verified lab technician is required.", status_code=422)
        if technician[0].facility_id != facility_id:
            raise HealthLinkError("Lab technician must belong to the diagnostic test facility.", status_code=422)

    def create(self, access: CurrentPatientAccess, requester: ProfessionalRoleRegistration, payload: DiagnosticTestCreateRequest) -> DiagnosticTestView:
        context = access.context
        appointments = AppointmentRepository(self.db)
        appointments._lock_for_queue(requester.id, context.appointment.appointment_date)
        locked = appointments.get_appointment_finish_context(
            appointment_id=context.appointment.id,
            doctor_role_registration_id=requester.id,
            for_update=True,
        )
        if (
            locked is None
            or locked.queue_entry.queue_status != QueueStatus.CURRENT.value
            or locked.appointment.status != AppointmentStatus.BOOKED.value
            or locked.practice_session.status != SessionStatus.ACTIVE.value
        ):
            raise HealthLinkError("The current consultation has changed. Reload before requesting a test.", status_code=409)
        visit = self.db.scalar(
            select(MedicalVisit).where(MedicalVisit.id == payload.visit_id)
            .with_for_update().execution_options(populate_existing=True)
        )
        if (
            visit is None
            or visit.appointment_id != locked.appointment.id
            or visit.citizen_id != locked.appointment.citizen_id
            or visit.doctor_role_registration_id != requester.id
            or visit.facility_id != locked.appointment.facility_id
            or visit.status != VisitStatus.DRAFT.value
        ):
            raise HealthLinkError("Visit does not match the active consultation.", status_code=409)
        if payload.catalog_code:
            name = test_name(payload.catalog_code)
            if payload.assigned_to_role_registration_id:
                raise HealthLinkError("The patient chooses the lab for this request.", status_code=422)
        else:
            if not payload.test_name:
                raise HealthLinkError("Choose a diagnostic test.", status_code=422)
            name = payload.test_name
            self._validate_technician(payload.assigned_to_role_registration_id, context.facility.id)
        item = self.repository.add(DiagnosticTest(
            citizen_id=visit.citizen_id,
            visit_id=visit.id,
            requested_by_role_registration_id=requester.id,
            assigned_to_role_registration_id=payload.assigned_to_role_registration_id,
            facility_id=None if payload.catalog_code else visit.facility_id,
            test_name=name,
            catalog_code=payload.catalog_code,
            instructions=payload.instructions,
            created_at=datetime.now(UTC),
        ))
        self.db.flush()
        record_notice(
            self.db, citizen_id=item.citizen_id, kind="DIAGNOSTIC",
            message=f"Your doctor requested {name}. Open Diagnostic tests to review the request.",
            dedupe_key=f"diagnostic-request:{item.id}",
        )
        self.db.commit()
        self.db.refresh(item)
        return self.view(item)

    def assign(self, test_id: uuid.UUID, requester: ProfessionalRoleRegistration, assignee_id: uuid.UUID | None) -> DiagnosticTestView:
        item = self.repository.get(test_id, for_update=True)
        if item is None or item.requested_by_role_registration_id != requester.id:
            raise HealthLinkError("Diagnostic test not found.", status_code=404)
        if item.catalog_code:
            raise HealthLinkError("The patient chooses the lab for this request.", status_code=409)
        if item.status != DiagnosticTestStatus.REQUESTED.value:
            raise HealthLinkError("Only requested tests can be assigned or reassigned.", status_code=409)
        if item.facility_id is None:
            raise HealthLinkError("Diagnostic test has no facility context.", status_code=409)
        self._validate_technician(assignee_id, item.facility_id)
        item.assigned_to_role_registration_id = assignee_id
        self.db.commit()
        self.db.refresh(item)
        return self.view(item)

    def transition(self, test_id: uuid.UUID, actor: ProfessionalRoleRegistration, target: DiagnosticTestStatus) -> DiagnosticTestView:
        item = self.repository.get(test_id, for_update=True)
        if item is None:
            raise HealthLinkError("Diagnostic test not found.", status_code=404)
        owner_id = item.requested_by_role_registration_id if actor.role.code == ProfessionalRoleCode.DOCTOR.value else item.assigned_to_role_registration_id
        if owner_id != actor.id:
            raise HealthLinkError("Diagnostic test not found.", status_code=404)
        current = DiagnosticTestStatus(item.status)
        if item.catalog_code:
            self.db.scalar(select(CitizenProfile.id).where(CitizenProfile.id == item.citizen_id).with_for_update())
            if self.db.scalar(qualifying_lab_sessions(item.citizen_id, item.catalog_code, item.created_at).limit(1)) is not None:
                raise HealthLinkError("This request already has a qualifying report.", status_code=409)
        allowed = False
        if actor.role.code == ProfessionalRoleCode.DOCTOR.value:
            allowed = item.requested_by_role_registration_id == actor.id and current is DiagnosticTestStatus.REQUESTED and target is DiagnosticTestStatus.CANCELLED
        elif actor.role.code == ProfessionalRoleCode.LAB_TECHNICIAN.value:
            allowed = item.assigned_to_role_registration_id == actor.id and current is DiagnosticTestStatus.REQUESTED and target is DiagnosticTestStatus.IN_PROGRESS
        if not allowed:
            raise HealthLinkError("Diagnostic test transition is not allowed.", status_code=409)
        item.status = target.value
        self.db.commit()
        self.db.refresh(item)
        return self.view(item)

    def eligible_technicians(self, facility_id: uuid.UUID, search: str | None) -> list[DiagnosticTechnicianChoice]:
        return [DiagnosticTechnicianChoice(role_registration_id=row["registration"].id, full_name=" ".join(filter(None, (row["user"].first_name, row["user"].last_name))), designation=row["registration"].designation, facility_id=row["facility"].id, facility_name=row["facility"].name) for row in self.repository.eligible_technicians(facility_id, search)]

    def list_citizen(self, citizen_id: uuid.UUID, page=1, page_size=50) -> list[DiagnosticTestView]:
        return self.views(self.repository.list_for_citizen(citizen_id, page, page_size), include_result=True)

    def list_professional(self, registration: ProfessionalRoleRegistration, page=1, page_size=50) -> list[DiagnosticTestView]:
        return self.views(self.repository.list_for_registration(registration.id, registration.role.code,
            page, page_size, registration.facility_id))

    def views(self, tests: list[DiagnosticTest], *, include_result: bool = False) -> list[DiagnosticTestView]:
        names = self.repository.names(tests)
        facilities = self.repository.facilities(tests)
        catalog_ids = [item.id for item in tests if item.catalog_code and item.status == DiagnosticTestStatus.REQUESTED]
        result = qualifying_lab_sessions(DiagnosticTest.citizen_id, DiagnosticTest.catalog_code, DiagnosticTest.created_at).order_by(
            DiagnosticPdf.tested_at, LabSession.id,
        ).correlate(DiagnosticTest).limit(1).scalar_subquery()
        matches = dict(self.db.execute(select(DiagnosticTest.id, result).where(DiagnosticTest.id.in_(catalog_ids))).all()) if catalog_ids else {}
        views = []
        for item in tests:
            view = self.view(item, names=names, facilities=facilities)
            if match := matches.get(item.id):
                view.status = DiagnosticTestStatus.COMPLETED
                if include_result:
                    view.result_session_id = match
            views.append(view)
        return views

    def view(self, item: DiagnosticTest, *, names: dict | None = None, facilities: dict | None = None) -> DiagnosticTestView:
        names = names or self.repository.names([item])
        facilities = facilities or self.repository.facilities([item])
        return DiagnosticTestView(id=item.id, citizen_id=item.citizen_id, visit_id=item.visit_id, requested_by_role_registration_id=item.requested_by_role_registration_id, assigned_to_role_registration_id=item.assigned_to_role_registration_id, facility_id=item.facility_id, facility_name=facilities.get(item.facility_id), test_name=item.test_name, catalog_code=item.catalog_code, instructions=item.instructions, status=item.status, requested_by_name=names.get(item.requested_by_role_registration_id, "Unknown professional"), assigned_to_name=names.get(item.assigned_to_role_registration_id), created_at=item.created_at, updated_at=item.updated_at)
