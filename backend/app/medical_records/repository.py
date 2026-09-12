from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import Integer, String, cast, func, literal, select, union_all
from sqlalchemy.orm import Session

from app.appointments.models import Appointment
from app.auth.models import User
from app.facilities.models import HealthcareFacility
from app.medical_records.schemas import MedicalHistoryResourceType
from app.prescriptions.models import Prescription, PrescriptionItem
from app.professionals.models import (
    HealthcareProfessionalProfile,
    ProfessionalRoleRegistration,
)
from app.visits.models import MedicalVisit, VisitStatus


class MedicalHistoryRepository:
    """Build one bounded timeline from authoritative clinical tables."""

    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _bounds(
        date_from: date | None,
        date_to: date | None,
    ) -> tuple[datetime | None, datetime | None]:
        start = (
            datetime.combine(date_from, time.min, tzinfo=UTC)
            if date_from is not None
            else None
        )
        end = (
            datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=UTC)
            if date_to is not None
            else None
        )
        return start, end

    @staticmethod
    def _apply_bounds(statement, occurred_at, start, end):
        if start is not None:
            statement = statement.where(occurred_at >= start)
        if end is not None:
            statement = statement.where(occurred_at < end)
        return statement

    def _visit_statement(
        self,
        citizen_id: uuid.UUID,
        *,
        start: datetime | None,
        end: datetime | None,
    ):
        statement = (
            select(
                literal(MedicalHistoryResourceType.VISIT.value).label(
                    "resource_type"
                ),
                MedicalVisit.id.label("resource_id"),
                MedicalVisit.finalized_at.label("occurred_at"),
                literal("Medical visit").label("title"),
                MedicalVisit.diagnosis.label("subtitle"),
                HealthcareFacility.name.label("facility_name"),
                User.first_name.label("professional_first_name"),
                User.last_name.label("professional_last_name"),
                MedicalVisit.status.label("status"),
                MedicalVisit.chief_complaint.label("summary"),
                MedicalVisit.appointment_id.label("appointment_id"),
                Appointment.serial_number.label("serial_number"),
                cast(literal(None), Integer).label("item_count"),
            )
            .join(
                ProfessionalRoleRegistration,
                ProfessionalRoleRegistration.id
                == MedicalVisit.doctor_role_registration_id,
            )
            .join(
                HealthcareProfessionalProfile,
                HealthcareProfessionalProfile.id
                == ProfessionalRoleRegistration.professional_id,
            )
            .join(User, User.id == HealthcareProfessionalProfile.user_id)
            .join(
                HealthcareFacility,
                HealthcareFacility.id == MedicalVisit.facility_id,
            )
            .outerjoin(Appointment, Appointment.id == MedicalVisit.appointment_id)
            .where(
                MedicalVisit.citizen_id == citizen_id,
                MedicalVisit.status == VisitStatus.FINALIZED.value,
                MedicalVisit.finalized_at.is_not(None),
            )
        )
        return self._apply_bounds(
            statement, MedicalVisit.finalized_at, start, end
        )

    def _prescription_statement(
        self,
        citizen_id: uuid.UUID,
        *,
        start: datetime | None,
        end: datetime | None,
    ):
        item_count = (
            select(func.count(PrescriptionItem.id))
            .where(PrescriptionItem.prescription_id == Prescription.id)
            .correlate(Prescription)
            .scalar_subquery()
        )
        statement = (
            select(
                literal(MedicalHistoryResourceType.PRESCRIPTION.value).label(
                    "resource_type"
                ),
                Prescription.id.label("resource_id"),
                Prescription.created_at.label("occurred_at"),
                literal("Prescription").label("title"),
                cast(literal(None), String).label("subtitle"),
                HealthcareFacility.name.label("facility_name"),
                User.first_name.label("professional_first_name"),
                User.last_name.label("professional_last_name"),
                literal("AVAILABLE").label("status"),
                Prescription.diagnostic_information.label("summary"),
                MedicalVisit.appointment_id.label("appointment_id"),
                Appointment.serial_number.label("serial_number"),
                item_count.label("item_count"),
            )
            .join(MedicalVisit, MedicalVisit.id == Prescription.visit_id)
            .join(
                ProfessionalRoleRegistration,
                ProfessionalRoleRegistration.id
                == Prescription.author_doctor_role_registration_id,
            )
            .join(
                HealthcareProfessionalProfile,
                HealthcareProfessionalProfile.id
                == ProfessionalRoleRegistration.professional_id,
            )
            .join(User, User.id == HealthcareProfessionalProfile.user_id)
            .join(
                HealthcareFacility,
                HealthcareFacility.id == MedicalVisit.facility_id,
            )
            .outerjoin(Appointment, Appointment.id == MedicalVisit.appointment_id)
            .where(
                Prescription.citizen_id == citizen_id,
                MedicalVisit.status == VisitStatus.FINALIZED.value,
                MedicalVisit.finalized_at.is_not(None),
            )
        )
        return self._apply_bounds(statement, Prescription.created_at, start, end)

    def list_events(
        self,
        citizen_id: uuid.UUID,
        *,
        resource_type: MedicalHistoryResourceType | None,
        date_from: date | None,
        date_to: date | None,
        offset: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        start, end = self._bounds(date_from, date_to)
        statements = []
        if resource_type in (None, MedicalHistoryResourceType.VISIT):
            statements.append(
                self._visit_statement(citizen_id, start=start, end=end)
            )
        if resource_type in (None, MedicalHistoryResourceType.PRESCRIPTION):
            statements.append(
                self._prescription_statement(citizen_id, start=start, end=end)
            )

        combined = (
            union_all(*statements).subquery("medical_history_events")
            if len(statements) > 1
            else statements[0].subquery("medical_history_events")
        )
        total = self.db.scalar(select(func.count()).select_from(combined)) or 0
        rows = self.db.execute(
            select(combined)
            .order_by(
                combined.c.occurred_at.desc(),
                combined.c.resource_type.asc(),
                combined.c.resource_id.desc(),
            )
            .offset(offset)
            .limit(limit)
        ).mappings()
        return [dict(row) for row in rows], total


__all__ = ["MedicalHistoryRepository"]
