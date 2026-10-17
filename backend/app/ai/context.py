from __future__ import annotations

import re
import uuid
from collections import defaultdict
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ai.schemas import (
    AIDiagnosticReportContext,
    AIEmergencyContext,
    AILabResultContext,
    AIPrescriptionContext,
    AIPrescriptionItemContext,
    AIProfileContext,
    AIRecordContext,
    AIVisitContext,
)
from app.citizens.models import CitizenProfile
from app.diagnostics.models import DiagnosticTest
from app.diagnostics.report_models import LabReport, LabReportItem
from app.emergency.models import EmergencyProfile
from app.prescriptions.models import Prescription
from app.visits.models import MedicalVisit, VisitStatus


_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_UUID = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
    re.I,
)
_LABELLED_IDENTIFIER = re.compile(
    r"\b(?:nid|national id|birth certificate|bcn)\s*(?:number|no\.?|#)?\s*[:=-]?\s*[A-Z0-9-]+",
    re.I,
)
_PHONE = re.compile(r"(?<!\w)(?:\+?88)?01[3-9]\d{8}(?!\w)")
_LONG_NUMBER = re.compile(r"(?<!\w)\d{8,17}(?!\w)")


def sanitize_clinical_text(
    value: str | None,
    *,
    limit: int = 1_200,
    redact_terms: tuple[str, ...] = (),
) -> str | None:
    """Remove common direct identifiers from bounded clinical free text."""

    if not value:
        return None
    cleaned = " ".join(value.split())
    cleaned = _EMAIL.sub("[redacted email]", cleaned)
    cleaned = _UUID.sub("[redacted identifier]", cleaned)
    cleaned = _LABELLED_IDENTIFIER.sub("[redacted identifier]", cleaned)
    cleaned = _PHONE.sub("[redacted phone]", cleaned)
    cleaned = _LONG_NUMBER.sub("[redacted number]", cleaned)
    for term in sorted(redact_terms, key=len, reverse=True):
        normalized_term = term.strip()
        if len(normalized_term) >= 3:
            cleaned = re.sub(
                re.escape(normalized_term),
                "[redacted identity]",
                cleaned,
                flags=re.I,
            )
    return cleaned[:limit]


def _age_group(date_of_birth: date, today: date) -> str:
    years = today.year - date_of_birth.year - (
        (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
    )
    if years < 1:
        return "under 1"
    if years <= 4:
        return "1-4"
    if years <= 11:
        return "5-11"
    if years <= 17:
        return "12-17"
    lower = (years // 10) * 10
    return "80+" if lower >= 80 else f"{lower}-{lower + 9}"


class AIRecordContextBuilder:
    """Load only finalized, citizen-owned records needed for AI guidance."""

    def __init__(
        self,
        db: Session,
        *,
        max_records: int,
        redact_terms: tuple[str, ...] = (),
    ) -> None:
        self.db = db
        self.max_records = max_records
        self.redact_terms = redact_terms

    def _sanitize(self, value: str | None, *, limit: int = 1_200) -> str | None:
        return sanitize_clinical_text(
            value,
            limit=limit,
            redact_terms=self.redact_terms,
        )

    def build(self, citizen: CitizenProfile) -> AIRecordContext:
        visits = self._visits(citizen.id)
        prescriptions = self._prescriptions(citizen.id)
        diagnostic_reports = self._diagnostic_reports(citizen.id)
        emergency = self.db.get(EmergencyProfile, citizen.id)

        return AIRecordContext(
            profile=AIProfileContext(
                age_group=_age_group(citizen.date_of_birth, date.today()),
                gender=citizen.gender,
                blood_group=citizen.blood_group,
            ),
            emergency_profile=(
                AIEmergencyContext(
                    allergies=self._sanitize(emergency.allergies),
                    chronic_conditions=self._sanitize(
                        emergency.chronic_conditions
                    ),
                    current_medications=self._sanitize(
                        emergency.current_medications
                    ),
                    special_notes=self._sanitize(emergency.special_notes),
                )
                if emergency
                else None
            ),
            visits=visits,
            prescriptions=prescriptions,
            diagnostic_reports=diagnostic_reports,
        )

    def _visits(self, citizen_id: uuid.UUID) -> list[AIVisitContext]:
        records = self.db.scalars(
            select(MedicalVisit)
            .where(
                MedicalVisit.citizen_id == citizen_id,
                MedicalVisit.status == VisitStatus.FINALIZED.value,
            )
            .order_by(MedicalVisit.visit_date.desc(), MedicalVisit.id.desc())
            .limit(self.max_records)
        ).all()
        return [
            AIVisitContext(
                visit_date=record.visit_date,
                chief_complaint=self._sanitize(record.chief_complaint),
                recorded_diagnosis=self._sanitize(record.diagnosis),
                clinical_notes=self._sanitize(record.clinical_notes),
                follow_up_instructions=self._sanitize(
                    record.follow_up_instructions
                ),
            )
            for record in records
        ]

    def _prescriptions(
        self,
        citizen_id: uuid.UUID,
    ) -> list[AIPrescriptionContext]:
        records = self.db.scalars(
            select(Prescription)
            .join(MedicalVisit, MedicalVisit.id == Prescription.visit_id)
            .options(selectinload(Prescription.items))
            .where(
                Prescription.citizen_id == citizen_id,
                MedicalVisit.status == VisitStatus.FINALIZED.value,
            )
            .order_by(Prescription.created_at.desc(), Prescription.id.desc())
            .limit(self.max_records)
        ).all()
        return [
            AIPrescriptionContext(
                created_at=record.created_at,
                diagnostic_information=self._sanitize(
                    record.diagnostic_information
                ),
                medical_advice=self._sanitize(record.medical_advice),
                notes=self._sanitize(record.notes),
                medicines=[
                    AIPrescriptionItemContext(
                        medicine_name=self._sanitize(
                            item.medicine_name,
                            limit=200,
                        )
                        or "[redacted]",
                        dosage=self._sanitize(item.dosage, limit=100)
                        or "[not recorded]",
                        frequency=self._sanitize(
                            item.frequency,
                            limit=100,
                        )
                        or "[not recorded]",
                        duration=self._sanitize(item.duration, limit=100)
                        or "[not recorded]",
                        instructions=self._sanitize(item.instructions),
                    )
                    for item in record.items[:20]
                ],
            )
            for record in records
        ]

    def _diagnostic_reports(
        self,
        citizen_id: uuid.UUID,
    ) -> list[AIDiagnosticReportContext]:
        rows = self.db.execute(
            select(LabReport, DiagnosticTest.test_name)
            .join(
                DiagnosticTest,
                DiagnosticTest.id == LabReport.diagnostic_test_id,
            )
            .where(
                LabReport.citizen_id == citizen_id,
                LabReport.status == "FINALIZED",
            )
            .order_by(LabReport.report_date.desc(), LabReport.id.desc())
            .limit(self.max_records)
        ).all()
        report_ids = [report.id for report, _ in rows]
        items_by_report: dict[uuid.UUID, list[LabReportItem]] = defaultdict(list)
        if report_ids:
            items = self.db.scalars(
                select(LabReportItem)
                .where(LabReportItem.lab_report_id.in_(report_ids))
                .order_by(LabReportItem.id)
            ).all()
            for item in items:
                if len(items_by_report[item.lab_report_id]) < 30:
                    items_by_report[item.lab_report_id].append(item)

        return [
            AIDiagnosticReportContext(
                report_date=report.report_date,
                test_name=self._sanitize(test_name, limit=255)
                or "Diagnostic test",
                summary=self._sanitize(report.summary),
                results=[
                    AILabResultContext(
                        parameter=self._sanitize(
                            item.parameter_name,
                            limit=150,
                        )
                        or "Result",
                        result=self._sanitize(
                            item.result_value_text,
                            limit=500,
                        )
                        or "[not recorded]",
                        unit=self._sanitize(item.unit, limit=50),
                        reference_range=self._sanitize(
                            item.reference_range,
                            limit=150,
                        ),
                        flag=self._sanitize(item.flag, limit=50),
                    )
                    for item in items_by_report[report.id]
                ],
            )
            for report, test_name in rows
        ]
