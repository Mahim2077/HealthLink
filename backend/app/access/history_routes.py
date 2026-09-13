from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import String, cast, literal, select, union_all
from sqlalchemy.orm import Session

from app.access.policy import ClinicalReadPolicy
from app.auth.dependencies import AuthContext, get_current_auth_context
from app.clinical_audit.service import AuditService
from app.core.exceptions import HealthLinkError
from app.db.session import get_db
from app.diagnostics.report_models import LabReport
from app.emergency.service import EmergencyProfileService
from app.prescriptions.models import Prescription
from app.visits.models import MedicalVisit

router = APIRouter(tags=["shared-medical-records"])
Auth = Annotated[AuthContext, Depends(get_current_auth_context)]
Database = Annotated[Session, Depends(get_db)]


@router.get("/professionals/patients/{citizen_id}/medical-history")
def history(citizen_id: UUID, auth: Auth, db: Database,
            record_type: Literal["VISIT", "PRESCRIPTION", "LAB_REPORT"] | None = None,
            page: Annotated[int, Query(ge=1, le=10000)] = 1):
    policy = ClinicalReadPolicy(db)
    policy.doctor(auth)
    decision = policy.authorize(auth, citizen_id, record_type or "MEDICAL_HISTORY")
    statements = []
    if record_type in (None, "VISIT"):
        statements.append(select(MedicalVisit.id.label("id"), literal("VISIT").label("resource_type"),
            literal("Medical visit").label("title"), MedicalVisit.finalized_at.label("occurred_at"),
            MedicalVisit.chief_complaint.label("summary"), cast(literal(None), String).label("detail_id"))
            .where(MedicalVisit.citizen_id == citizen_id, MedicalVisit.status == "FINALIZED", MedicalVisit.finalized_at.is_not(None)))
    if record_type in (None, "PRESCRIPTION"):
        statements.append(select(Prescription.id.label("id"), literal("PRESCRIPTION").label("resource_type"),
            literal("Prescription").label("title"), Prescription.created_at.label("occurred_at"),
            Prescription.diagnostic_information.label("summary"), cast(Prescription.id, String).label("detail_id"))
            .join(MedicalVisit, MedicalVisit.id == Prescription.visit_id).where(Prescription.citizen_id == citizen_id,
                MedicalVisit.status == "FINALIZED", MedicalVisit.finalized_at.is_not(None)))
    if record_type in (None, "LAB_REPORT"):
        statements.append(select(LabReport.id.label("id"), literal("LAB_REPORT").label("resource_type"),
            literal("Lab report").label("title"), LabReport.finalized_at.label("occurred_at"),
            LabReport.summary.label("summary"), cast(LabReport.diagnostic_test_id, String).label("detail_id"))
            .where(LabReport.citizen_id == citizen_id, LabReport.status == "FINALIZED", LabReport.finalized_at.is_not(None)))
    combined = union_all(*statements).subquery()
    rows = db.execute(select(combined).order_by(combined.c.occurred_at.desc(), combined.c.resource_type, combined.c.id)
        .offset((page - 1) * 20).limit(21)).mappings().all()
    records = []
    for row in rows[:20]:
        resource = row["resource_type"]
        detail_id = str(UUID(row["detail_id"])) if row["detail_id"] else None
        url = f"/professional/prescriptions/{detail_id}" if resource == "PRESCRIPTION" else f"/professional/diagnostics/{detail_id}/report" if resource == "LAB_REPORT" else None
        records.append({"id": row["id"], "resource_type": resource, "title": row["title"],
                        "occurred_at": row["occurred_at"], "summary": row["summary"], "detail_url": url})
    AuditService(db).record(auth=auth, citizen_id=citizen_id, resource_type=record_type or "MEDICAL_HISTORY", access_source=decision.source)
    return {"records": records, "page": page, "has_next": len(rows) > 20}


@router.get("/professionals/patients/{citizen_id}/visits/{visit_id}")
def visit(citizen_id: UUID, visit_id: UUID, auth: Auth, db: Database):
    policy = ClinicalReadPolicy(db)
    policy.doctor(auth)
    record = db.scalar(select(MedicalVisit).where(MedicalVisit.id == visit_id,
        MedicalVisit.citizen_id == citizen_id, MedicalVisit.status == "FINALIZED", MedicalVisit.finalized_at.is_not(None)))
    if record is None:
        raise HealthLinkError("Clinical record not found.", status_code=404)
    decision = policy.authorize(auth, citizen_id, "VISIT", resource_id=visit_id, author_role_id=record.doctor_role_registration_id)
    result = {"id": record.id, "chief_complaint": record.chief_complaint, "diagnosis": record.diagnosis,
              "clinical_notes": record.clinical_notes, "follow_up_instructions": record.follow_up_instructions,
              "finalized_at": record.finalized_at}
    AuditService(db).record(auth=auth, citizen_id=citizen_id, resource_type="VISIT", resource_id=visit_id, access_source=decision.source)
    return result


@router.get("/professionals/patients/{citizen_id}/emergency-profile")
def emergency(citizen_id: UUID, auth: Auth, db: Database):
    policy = ClinicalReadPolicy(db)
    policy.doctor(auth)
    decision = policy.authorize(auth, citizen_id, "EMERGENCY_PROFILE")
    result = EmergencyProfileService(db).read(citizen_id)
    AuditService(db).record(auth=auth, citizen_id=citizen_id, resource_type="EMERGENCY_PROFILE", access_source=decision.source)
    return result
