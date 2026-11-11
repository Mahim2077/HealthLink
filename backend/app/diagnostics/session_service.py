from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.access.policy import ClinicalReadPolicy
from app.auth.constants import Portal
from app.auth.dependencies import AuthContext
from app.auth.models import User
from app.citizens.models import CitizenProfile
from app.clinical_audit.service import AuditService
from app.core.config import Settings
from app.core.exceptions import HealthLinkError
from app.diagnostics.catalog import test_name
from app.diagnostics.pdf_screening import screen_pdf
from app.diagnostics.session_models import DiagnosticPdf, LabSession, LabSessionStatus as Status
from app.diagnostics.session_schemas import AcceptLabSession, CloseReason, CreateLabSession, LabSessionView
from app.facilities.models import HealthcareFacility
from app.professionals.models import ProfessionalRoleRegistration
from app.reminders.inbox import record_notice


ACTIVE = {Status.ACCEPTED, Status.CHECKED_IN, Status.COLLECTED, Status.PERFORMED}
TRANSITIONS = {
    Status.CHECKED_IN: {Status.ACCEPTED},
    Status.COLLECTED: {Status.CHECKED_IN},
    Status.PERFORMED: {Status.CHECKED_IN, Status.COLLECTED},
}
CODE_LIFETIME = timedelta(hours=24)


def utc(value: datetime) -> datetime:
    return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)


def effective_status(item: LabSession, now: datetime) -> str:
    if item.status == Status.ACCEPTED and item.attendance_deadline and utc(item.attendance_deadline) <= now:
        return Status.EXPIRED
    return item.status


class LabSessionService:
    def __init__(self, db: Session):
        self.db = db

    def _get(self, session_id: UUID, *, lock: bool = False) -> LabSession:
        query = select(LabSession).where(LabSession.id == session_id)
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        item = self.db.scalar(query)
        if item is None:
            raise HealthLinkError("Lab session not found.", status_code=404)
        return item

    def _facility(self, actor: ProfessionalRoleRegistration) -> HealthcareFacility:
        facility = self.db.get(HealthcareFacility, actor.facility_id) if actor.facility_id else None
        if facility is None or not facility.is_active:
            raise HealthLinkError("An active lab facility is required.", status_code=403)
        return facility

    def _assigned(self, item: LabSession, actor: ProfessionalRoleRegistration) -> None:
        if item.technician_id != actor.id or item.facility_id != actor.facility_id:
            raise HealthLinkError("Lab session not found.", status_code=404)
        self._facility(actor)

    def _draft(self, item: LabSession) -> DiagnosticPdf | None:
        return self.db.scalar(select(DiagnosticPdf).where(
            DiagnosticPdf.session_id == item.id, DiagnosticPdf.published_at.is_(None),
        ).order_by(DiagnosticPdf.version.desc()).limit(1))

    @staticmethod
    def _view_query(lab: bool):
        query = (
            select(LabSession, HealthcareFacility.name, DiagnosticPdf.catalog_code)
            .outerjoin(HealthcareFacility, HealthcareFacility.id == LabSession.facility_id)
            .outerjoin(DiagnosticPdf, (DiagnosticPdf.session_id == LabSession.id) & (DiagnosticPdf.version == LabSession.current_report_version))
        )
        if lab:
            draft = aliased(DiagnosticPdf)
            query = (query.outerjoin(CitizenProfile, CitizenProfile.id == LabSession.citizen_id)
                     .outerjoin(User, User.id == CitizenProfile.user_id)
                     .outerjoin(draft, (draft.session_id == LabSession.id) & draft.published_at.is_(None))
                     .add_columns(User.first_name, User.last_name, draft.version, draft.catalog_code, draft.tested_at))
        return query

    @staticmethod
    def _view_row(row, *, citizen: bool) -> LabSessionView:
        item, facility_name, report_code, *lab_details = row
        now = datetime.now(UTC)
        status = effective_status(item, now)
        first, last, draft_version, draft_code, draft_time = lab_details or (None, None, None, None, None)
        return LabSessionView(
            id=item.id, catalog_code=item.catalog_code, test_name=test_name(item.catalog_code),
            status=status, created_at=utc(item.created_at),
            attendance_deadline=utc(item.attendance_deadline) if item.attendance_deadline else None,
            facility_name=facility_name, closed_reason=item.closed_reason,
            share_code=item.share_code if citizen and status == Status.REQUESTED and now < utc(item.created_at) + CODE_LIFETIME else None,
            patient_name=" ".join(filter(None, (first, last))) or None, report_version=item.current_report_version,
            report_test_name=test_name(report_code) if report_code else None, draft_version=draft_version,
            draft_test_name=test_name(draft_code) if draft_code else None,
            draft_tested_at=utc(draft_time) if draft_time else None,
        )

    def view(self, item: LabSession, *, citizen: bool = False, lab: bool = False) -> LabSessionView:
        row = self.db.execute(self._view_query(lab).where(LabSession.id == item.id)).one()
        return self._view_row(row, citizen=citizen)

    def list(self, owner: UUID, page: int, *, citizen: bool, facility_id: UUID | None = None) -> list[LabSessionView]:
        condition = LabSession.citizen_id == owner if citizen else (
            (LabSession.technician_id == owner) & (LabSession.facility_id == facility_id)
        )
        rows = self.db.execute(self._view_query(not citizen).where(condition).order_by(
            LabSession.created_at.desc(), LabSession.id.desc()
        ).offset((page - 1) * 20).limit(21))
        return [self._view_row(row, citizen=citizen) for row in rows]

    def _commit(self, item: LabSession, auth: AuthContext, action: str) -> None:
        AuditService(self.db).record(auth=auth, citizen_id=item.citizen_id, resource_type="DIAGNOSTIC_SESSION",
                                     resource_id=item.id, action=action, commit=False)
        self.db.commit()

    def create(self, citizen_id: UUID, payload: CreateLabSession, auth: AuthContext) -> LabSessionView:
        test_name(payload.catalog_code)
        self.db.scalar(select(CitizenProfile.id).where(CitizenProfile.id == citizen_id).with_for_update())
        existing = self.db.get(LabSession, payload.id)
        if existing:
            if existing.citizen_id != citizen_id or existing.catalog_code != payload.catalog_code:
                raise HealthLinkError("This session reference is already in use.", status_code=409)
            return self.view(existing, citizen=True)
        item = LabSession(id=payload.id, citizen_id=citizen_id, catalog_code=payload.catalog_code,
                          share_code=token_urlsafe(16), created_at=datetime.now(UTC))
        self.db.add(item)
        self._commit(item, auth, "CREATE")
        return self.view(item, citizen=True)

    def cancel(self, citizen_id: UUID, session_id: UUID, auth: AuthContext) -> LabSessionView:
        item = self._get(session_id, lock=True)
        if item.citizen_id != citizen_id:
            raise HealthLinkError("Lab session not found.", status_code=404)
        if item.status == Status.CANCELLED:
            return self.view(item, citizen=True)
        if item.status != Status.REQUESTED:
            raise HealthLinkError("Only sessions awaiting acceptance can be cancelled.", status_code=409)
        item.status = Status.CANCELLED
        item.share_code = None
        self._commit(item, auth, "CANCEL")
        return self.view(item, citizen=True)

    def accept(self, actor: ProfessionalRoleRegistration, payload: AcceptLabSession, auth: AuthContext) -> LabSessionView:
        facility = self._facility(actor)
        item = self.db.scalar(select(LabSession).where(LabSession.share_code == payload.code)
                              .with_for_update().execution_options(populate_existing=True))
        now = datetime.now(UTC)
        if item is None or item.status != Status.REQUESTED or now >= utc(item.created_at) + CODE_LIFETIME:
            raise HealthLinkError("Session code is invalid, expired, or already used.", status_code=404)
        if not now < payload.attendance_deadline <= now + timedelta(days=30):
            raise HealthLinkError("Choose an attendance deadline within the next 30 days.", status_code=422)
        item.technician_id = actor.id
        item.facility_id = facility.id
        item.attendance_deadline = utc(payload.attendance_deadline)
        item.status = Status.ACCEPTED
        item.share_code = None
        record_notice(
            self.db, citizen_id=item.citizen_id, kind="DIAGNOSTIC",
            message=f"{facility.name} accepted your {test_name(item.catalog_code)} session. Open Diagnostic tests for attendance details.",
            dedupe_key=f"diagnostic-accepted:{item.id}",
        )
        self._commit(item, auth, "ACCEPT")
        return self.view(item, lab=True)

    def transition(self, session_id: UUID, actor: ProfessionalRoleRegistration, target: Status, auth: AuthContext,
                   tested_at: datetime | None = None) -> LabSessionView:
        item = self._get(session_id, lock=True)
        self._assigned(item, actor)
        now = datetime.now(UTC)
        if target not in TRANSITIONS or effective_status(item, now) not in TRANSITIONS[target]:
            raise HealthLinkError("This step is unavailable for the current session status.", status_code=409)
        actual = utc(tested_at) if tested_at else now
        if target == Status.CHECKED_IN:
            item.checked_in_at = now
        elif not item.checked_in_at or not utc(item.collected_at or item.checked_in_at) <= actual <= now:
            raise HealthLinkError("Enter the actual step time, between check-in or collection and now.", status_code=422)
        item.status = target
        if target == Status.COLLECTED:
            item.collected_at = actual
        if target == Status.PERFORMED:
            item.performed_at = actual
        self._commit(item, auth, target.value)
        return self.view(item, lab=True)

    def close(self, session_id: UUID, reason: CloseReason, auth: AuthContext, *,
              actor: ProfessionalRoleRegistration | None = None, facility_id: UUID | None = None) -> LabSessionView:
        item = self._get(session_id, lock=True)
        if actor:
            self._assigned(item, actor)
        elif item.facility_id != facility_id or facility_id is None:
            raise HealthLinkError("Lab session not found.", status_code=404)
        if effective_status(item, datetime.now(UTC)) not in ACTIVE:
            raise HealthLinkError("Only active sessions before publication can be closed.", status_code=409)
        draft = self._draft(item)
        if draft:
            self.db.delete(draft)
        item.status = Status.UNABLE
        item.closed_reason = reason
        record_notice(
            self.db, citizen_id=item.citizen_id, kind="DIAGNOSTIC",
            message=f"Your {test_name(item.catalog_code)} session was closed. Open Diagnostic tests for details.",
            dedupe_key=f"diagnostic-closed:{item.id}",
        )
        self._commit(item, auth, "CLOSE")
        return self.view(item, lab=actor is not None)

    def stage_pdf(self, session_id: UUID, actor: ProfessionalRoleRegistration, content: bytes, settings: Settings,
                  catalog_code: str | None, tested_at: datetime | None, auth: AuthContext) -> LabSessionView:
        item = self._get(session_id)
        self._assigned(item, actor)
        if item.status not in {Status.PERFORMED, Status.PUBLISHED}:
            raise HealthLinkError("Mark the test performed before uploading a report.", status_code=409)
        screened = screen_pdf(content, settings)
        item = self._get(session_id, lock=True)
        self._assigned(item, actor)
        if item.status not in {Status.PERFORMED, Status.PUBLISHED} or not item.performed_at:
            raise HealthLinkError("The session can no longer accept this report.", status_code=409)
        current = self.db.get(DiagnosticPdf, (item.id, item.current_report_version)) if item.current_report_version else None
        code = catalog_code or (current.catalog_code if current else item.catalog_code)
        test_name(code)
        performed_at = utc(item.collected_at or item.performed_at)
        verified_time = utc(tested_at) if tested_at else utc(current.tested_at) if current else performed_at
        if tested_at and not utc(item.checked_in_at or item.created_at) <= verified_time <= datetime.now(UTC):
            raise HealthLinkError("Choose a test time within the session.", status_code=422)
        if item.status == Status.PERFORMED and (code != item.catalog_code or tested_at):
            raise HealthLinkError("The first report must match the session’s test type and recorded test time.", status_code=422)
        digest = sha256(content).hexdigest()
        previous = self._draft(item)
        if previous and previous.sha256 == digest and previous.catalog_code == code and utc(previous.tested_at) == verified_time:
            return self.view(item, lab=True)
        next_version = self.db.scalar(select(func.max(DiagnosticPdf.version)).where(DiagnosticPdf.session_id == item.id)) or 0
        if previous:
            self.db.delete(previous)
        self.db.add(DiagnosticPdf(session_id=item.id, version=next_version + 1, catalog_code=code,
                                  tested_at=verified_time, sha256=digest, content=content))
        self._commit(item, auth, "SCREENED_PDF" if screened else "UPLOAD_PDF")
        return self.view(item, lab=True)

    def publish(self, session_id: UUID, version: int, actor: ProfessionalRoleRegistration, auth: AuthContext) -> LabSessionView:
        item = self._get(session_id, lock=True)
        self._assigned(item, actor)
        if item.current_report_version == version:
            return self.view(item, lab=True)
        draft = self._draft(item)
        if item.status not in {Status.PERFORMED, Status.PUBLISHED} or draft is None or draft.version != version:
            raise HealthLinkError("Refresh and confirm the current PDF before publishing.", status_code=409)
        self.db.scalar(select(CitizenProfile.id).where(CitizenProfile.id == item.citizen_id).with_for_update())
        draft.published_at = datetime.now(UTC)
        item.current_report_version = version
        item.status = Status.PUBLISHED
        record_notice(
            self.db, citizen_id=item.citizen_id, kind="DIAGNOSTIC",
            message=f"Your {test_name(draft.catalog_code)} report is available in Diagnostic tests.",
            dedupe_key=f"diagnostic-published:{item.id}:{version}",
        )
        self._commit(item, auth, "PUBLISH")
        return self.view(item, lab=True)

    def withdraw(self, session_id: UUID, version: int, actor: ProfessionalRoleRegistration, auth: AuthContext) -> LabSessionView:
        item = self._get(session_id, lock=True)
        self._assigned(item, actor)
        if item.current_report_version != version:
            raise HealthLinkError("Refresh and confirm the current PDF before withdrawing it.", status_code=409)
        self.db.scalar(select(CitizenProfile.id).where(CitizenProfile.id == item.citizen_id).with_for_update())
        item.current_report_version = None
        draft = self._draft(item)
        if draft:
            self.db.delete(draft)
        record_notice(
            self.db, citizen_id=item.citizen_id, kind="DIAGNOSTIC",
            message="A diagnostic report was withdrawn. Open Diagnostic tests for the current status.",
            dedupe_key=f"diagnostic-withdrawn:{item.id}:{version}",
        )
        self._commit(item, auth, "WITHDRAW")
        return self.view(item, lab=True)

    def read_pdf(self, session_id: UUID, auth: AuthContext) -> bytes:
        item = self._get(session_id, lock=True)
        if item.current_report_version is None:
            raise HealthLinkError("Diagnostic PDF not found.", status_code=404)
        decision = ClinicalReadPolicy(self.db).authorize(auth, item.citizen_id, "LAB_REPORT", resource_id=item.id)
        report = self.db.get(DiagnosticPdf, (item.id, item.current_report_version))
        if report is None:
            raise HealthLinkError("Diagnostic PDF not found.", status_code=404)
        content = report.content
        AuditService(self.db).record(auth=auth, citizen_id=item.citizen_id, resource_type="LAB_REPORT",
                                     resource_id=item.id, access_source=decision.source)
        return content

    def read_lab_pdf(self, session_id: UUID, version: int, actor: ProfessionalRoleRegistration, auth: AuthContext) -> bytes:
        item = self._get(session_id, lock=True)
        self._assigned(item, actor)
        if item.status not in {Status.PERFORMED, Status.PUBLISHED}:
            raise HealthLinkError("Diagnostic PDF not found.", status_code=404)
        report = self._draft(item)
        if report is None or report.version != version:
            if item.current_report_version != version:
                raise HealthLinkError("Diagnostic PDF not found.", status_code=404)
            report = self.db.get(DiagnosticPdf, (item.id, version))
        content = report.content
        AuditService(self.db).record(auth=auth, citizen_id=item.citizen_id, resource_type="LAB_REPORT",
                                     resource_id=item.id, access_source="ASSIGNMENT")
        return content
