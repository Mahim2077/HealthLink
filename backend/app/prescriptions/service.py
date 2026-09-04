"""Phase 13 prescription service.

Owns the author-only-edit invariant and PDF regeneration. The route
handlers are intentionally thin — they capture HTTP concerns (auth,
status codes) while every multi-step rule lives here so it can be
exercised from unit tests without going through FastAPI.
"""
from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy.orm import Session

from app.citizens.models import CitizenProfile
from app.core.exceptions import HealthLinkError
from app.facilities.models import HealthcareFacility
from app.prescriptions.models import (
    Prescription,
    PrescriptionDocument,
    PrescriptionItem,
)
from app.prescriptions.pdf import (
    PrescriptionDoctor,
    PrescriptionItemView,
    PrescriptionPdfView,
    generate_prescription_pdf_bytes,
)
from app.prescriptions.repository import PrescriptionsRepository
from app.prescriptions.schemas import (
    PrescriptionCreateRequest,
    PrescriptionItemView as PrescriptionItemViewSchema,
    PrescriptionUpdateRequest,
    PrescriptionView,
)
from app.prescriptions.storage import (
    PrescriptionStorage,
    get_prescription_storage,
)
from app.professionals.models import (
    DoctorRegistrationDetail,
    HealthcareProfessionalProfile,
    ProfessionalRoleRegistration,
)
from app.visits.models import MedicalVisit


logger = logging.getLogger(__name__)


# Service-layer mirror of the PDF forbidden-pattern guard. The PDF
# generator raises ``ValueError`` when it detects NID/BCN-style text in
# any item instruction; we want to reject the request with HTTP 400 at
# the API boundary instead of surfacing a 500 from the render step.
_SERVICE_FORBIDDEN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bnid\b", re.IGNORECASE),
    re.compile(r"\bbcn\b", re.IGNORECASE),
)


def _assert_no_forbidden_payload_text(value: str | None, location: str) -> None:
    if not value:
        return
    for pattern in _SERVICE_FORBIDDEN_PATTERNS:
        if pattern.search(value):
            raise HealthLinkError(
                "Prescription text must not embed NID/BCN identifiers "
                f"({location}).",
                status_code=400,
            )


@dataclass(frozen=True)
class _DoctorHeader:
    """Internal convenience record built from the doctor profile."""

    full_name: str
    designation: str
    bm_dc_registration_no: str
    facility_name: str


def _ensure_visit_doctor_owns_visit(
    visit: MedicalVisit, doctor_role_registration_id: uuid.UUID
) -> None:
    if visit.doctor_role_registration_id != doctor_role_registration_id:
        # The author of the prescription must be the doctor who owns
        # the underlying visit — never a foreign doctor who happens
        # to have arrived at the queue later in the day.
        raise HealthLinkError(
            "Only the verified doctor who owns this visit may author "
            "the prescription.",
            status_code=403,
        )


def _doctor_header_for(
    db: Session, role_registration_id: uuid.UUID
) -> _DoctorHeader:
    registration = db.get(
        ProfessionalRoleRegistration, role_registration_id
    )
    if registration is None:
        raise HealthLinkError(
            "Author doctor role registration could not be resolved.",
            status_code=500,
        )
    profile = db.get(
        HealthcareProfessionalProfile, registration.professional_id
    )
    if profile is None:
        raise HealthLinkError(
            "Author doctor profile could not be resolved.",
            status_code=500,
        )
    doctor_detail = db.get(
        DoctorRegistrationDetail, role_registration_id
    )
    facility: HealthcareFacility | None = None
    if registration.facility_id is not None:
        facility = db.get(HealthcareFacility, registration.facility_id)
    user = profile.user
    return _DoctorHeader(
        full_name=f"{user.first_name} {user.last_name}",
        designation=(
            doctor_detail.designation
            if doctor_detail else "Medical Practitioner"
        ),
        bm_dc_registration_no=(
            doctor_detail.bmdc_registration_number
            if doctor_detail else ""
        ),
        facility_name=(
            facility.name if facility else "Unspecified facility"
        ),
    )


def _patient_summary(
    db: Session, citizen_id: uuid.UUID
) -> tuple[str, str]:
    profile = db.get(CitizenProfile, citizen_id)
    if profile is None:
        raise HealthLinkError(
            "Citizen profile could not be resolved.",
            status_code=500,
        )
    age_label = "Age not provided"
    if profile.date_of_birth is not None:
        today = datetime.now(timezone.utc).date()
        years = today.year - profile.date_of_birth.year - (
            (today.month, today.day)
            < (profile.date_of_birth.month, profile.date_of_birth.day)
        )
        age_label = (
            f"{years} years (DOB {profile.date_of_birth.isoformat()})"
        )
    user = profile.user
    return f"{user.first_name} {user.last_name}", age_label


def _serial_label(visit: MedicalVisit) -> str:
    appointment = visit.appointment if visit.appointment is not None else None
    if appointment is None and visit.appointment_id is not None:
        # ``visit`` may not be eager-loaded with appointment in every
        # call site; the appointment_id alone is enough to construct
        # a stable label.
        return f"appointment {visit.appointment_id}"
    if appointment is not None and appointment.serial_number is not None:
        return f"serial {appointment.serial_number}"
    return "walk-in"


def _build_pdf_view(
    db: Session, prescription: Prescription, items: list[PrescriptionItem]
) -> PrescriptionPdfView:
    visit = db.get(MedicalVisit, prescription.visit_id)
    if visit is None:
        raise HealthLinkError(
            "Underlying medical visit could not be resolved.",
            status_code=500,
        )
    doctor_header = _doctor_header_for(
        db, prescription.author_doctor_role_registration_id
    )
    patient_name, patient_age = _patient_summary(db, prescription.citizen_id)
    serial_label = _serial_label(visit)
    pdf_items = tuple(
        PrescriptionItemView(
            medicine_name=item.medicine_name,
            dosage=item.dosage,
            frequency=item.frequency,
            duration=item.duration,
            instructions=item.instructions,
        )
        for item in items
    )
    return PrescriptionPdfView(
        prescription_id=str(prescription.id),
        visit_date=visit.visit_date,
        doctor=PrescriptionDoctor(
            full_name=doctor_header.full_name,
            bm_dc_registration_no=doctor_header.bm_dc_registration_no,
            designation=doctor_header.designation,
            facility_name=doctor_header.facility_name,
        ),
        patient_name=patient_name,
        patient_age=patient_age,
        serial_label=serial_label,
        items=pdf_items,
        diagnostic_information=prescription.diagnostic_information,
        medical_advice=prescription.medical_advice,
        notes=prescription.notes,
    )


def _validate_payload_text(
    diagnostic_information: str | None,
    medical_advice: str | None,
    notes: str | None,
    items: Iterable,
) -> None:
    """Reject prescription text that would render NID/BCN into the PDF.

    The PDF generator performs the same scan; this service-level check
    guarantees the request fails with HTTP 400 instead of an internal
    server error and gives a stable code path for tests.
    """
    _assert_no_forbidden_payload_text(
        diagnostic_information, "diagnostic_information"
    )
    _assert_no_forbidden_payload_text(medical_advice, "medical_advice")
    _assert_no_forbidden_payload_text(notes, "notes")
    for index, item in enumerate(items):
        _assert_no_forbidden_payload_text(
            item.medicine_name, f"items[{index}].medicine_name"
        )
        _assert_no_forbidden_payload_text(
            item.dosage, f"items[{index}].dosage"
        )
        _assert_no_forbidden_payload_text(
            item.frequency, f"items[{index}].frequency"
        )
        _assert_no_forbidden_payload_text(
            item.duration, f"items[{index}].duration"
        )
        _assert_no_forbidden_payload_text(
            item.instructions, f"items[{index}].instructions"
        )


def _materialise_items(payload_items: Iterable) -> list[PrescriptionItem]:
    return [
        PrescriptionItem(
            id=uuid.uuid4(),
            medicine_name=item.medicine_name,
            dosage=item.dosage,
            frequency=item.frequency,
            duration=item.duration,
            instructions=item.instructions,
        )
        for item in payload_items
    ]


def _write_pdf(
    storage: PrescriptionStorage,
    repository: PrescriptionsRepository,
    prescription: Prescription,
    view: PrescriptionPdfView,
) -> tuple[PrescriptionDocument, str | None]:
    payload = generate_prescription_pdf_bytes(view)
    document = repository.get_document_for_prescription(prescription.id)
    previous_storage_key = (
        document.storage_key if document is not None else None
    )
    storage_key = storage.save(
        prescription.id,
        f"prescription-{uuid.uuid4().hex}.pdf",
        payload,
    )
    if document is None:
        document = PrescriptionDocument(
            id=uuid.uuid4(),
            prescription_id=prescription.id,
            storage_key=storage_key,
            file_name="prescription.pdf",
            content_type="application/pdf",
            file_size_bytes=len(payload),
        )
        repository.db.add(document)
    else:
        document.storage_key = storage_key
        document.file_name = "prescription.pdf"
        document.content_type = "application/pdf"
        document.file_size_bytes = len(payload)
        document.generated_at = datetime.now(timezone.utc)
    return document, previous_storage_key


def _prescription_view(prescription: Prescription) -> PrescriptionView:
    document = prescription.document
    return PrescriptionView(
        id=prescription.id,
        visit_id=prescription.visit_id,
        citizen_id=prescription.citizen_id,
        author_doctor_role_registration_id=prescription.author_doctor_role_registration_id,
        diagnostic_information=prescription.diagnostic_information,
        medical_advice=prescription.medical_advice,
        notes=prescription.notes,
        items=[
            PrescriptionItemViewSchema(
                id=item.id,
                medicine_name=item.medicine_name,
                dosage=item.dosage,
                frequency=item.frequency,
                duration=item.duration,
                instructions=item.instructions,
            )
            for item in prescription.items
        ],
        pdf_available=document is not None,
        pdf_file_name=document.file_name if document is not None else None,
        pdf_updated_at=document.updated_at if document is not None else None,
        created_at=prescription.created_at,
        updated_at=prescription.updated_at,
    )


class PrescriptionsService:
    """Author-only-edit prescription lifecycle for chamber visits."""

    def __init__(
        self,
        db: Session,
        storage: PrescriptionStorage | None = None,
    ) -> None:
        self._db = db
        self._repository = PrescriptionsRepository(db)
        self._storage = storage or get_prescription_storage()

    def _delete_storage_quietly(self, storage_key: str | None) -> None:
        if not storage_key:
            return
        try:
            self._storage.delete(storage_key)
        except Exception:  # pragma: no cover - best-effort orphan cleanup.
            logger.exception(
                "Could not delete superseded prescription PDF object."
            )

    def _reload_view(self, prescription_id: uuid.UUID) -> PrescriptionView:
        self._db.expire_all()
        prescription = self._repository.get_prescription_by_id(
            prescription_id
        )
        if prescription is None:  # pragma: no cover - invariant protection.
            raise HealthLinkError(
                "Prescription could not be reloaded.", status_code=500
            )
        return _prescription_view(prescription)

    def _commit_with_best_effort_pdf(
        self,
        prescription: Prescription,
    ) -> PrescriptionView:
        """Commit structured data even when PDF generation/storage fails.

        A new object is uploaded under a versioned key before the database
        document pointer is committed. On success the old object is removed.
        On render/upload failure the stale document row is removed and the
        structured prescription is still committed, making a later PUT a safe
        regeneration retry.
        """

        previous_document = self._repository.get_document_for_prescription(
            prescription.id
        )
        previous_storage_key = (
            previous_document.storage_key
            if previous_document is not None
            else None
        )
        new_storage_key: str | None = None

        try:
            pdf_view = _build_pdf_view(
                self._db, prescription, list(prescription.items)
            )
            document, previous_storage_key = _write_pdf(
                self._storage,
                self._repository,
                prescription,
                pdf_view,
            )
            new_storage_key = document.storage_key
        except Exception:
            logger.exception(
                "Prescription %s was saved without a PDF; regeneration is "
                "available through the author update flow.",
                prescription.id,
            )
            if previous_document is not None:
                self._db.delete(previous_document)
            try:
                self._db.commit()
            except Exception:
                self._db.rollback()
                self._delete_storage_quietly(new_storage_key)
                raise
            self._delete_storage_quietly(previous_storage_key)
            return self._reload_view(prescription.id)

        try:
            self._db.commit()
        except Exception:
            self._db.rollback()
            self._delete_storage_quietly(new_storage_key)
            raise

        if previous_storage_key != new_storage_key:
            self._delete_storage_quietly(previous_storage_key)
        return self._reload_view(prescription.id)

    # ---- read paths ---------------------------------------------------

    def read_for_doctor(
        self,
        doctor_role_registration_id: uuid.UUID,
        prescription_id: uuid.UUID,
    ) -> PrescriptionView:
        prescription = self._repository.get_prescription_by_id(prescription_id)
        if prescription is None:
            raise HealthLinkError(
                "Prescription not found.", status_code=404
            )
        # The route dependency already enforces author-only professional
        # access. Keep the visit ownership check here as a service-layer
        # invariant so direct callers cannot cross doctor boundaries.
        visit = self._repository.get_visit_for_prescription(prescription)
        if visit is None:
            raise HealthLinkError(
                "Underlying medical visit could not be resolved.",
                status_code=404,
            )
        if visit.doctor_role_registration_id != doctor_role_registration_id:
            raise HealthLinkError(
                "This prescription does not belong to your chamber "
                "queue.",
                status_code=403,
            )
        return _prescription_view(prescription)

    def read_for_citizen(
        self,
        citizen_id: uuid.UUID,
        prescription_id: uuid.UUID,
    ) -> PrescriptionView:
        prescription = self._repository.get_prescription_by_id(prescription_id)
        if prescription is None or prescription.citizen_id != citizen_id:
            raise HealthLinkError(
                "Prescription not found.", status_code=404
            )
        return _prescription_view(prescription)

    # ---- write paths --------------------------------------------------

    def create_for_visit(
        self,
        doctor_role_registration_id: uuid.UUID,
        visit_id: uuid.UUID,
        payload: PrescriptionCreateRequest,
    ) -> PrescriptionView:
        visit = self._db.get(MedicalVisit, visit_id)
        if visit is None:
            raise HealthLinkError(
                "Medical visit not found.", status_code=404
            )
        _ensure_visit_doctor_owns_visit(visit, doctor_role_registration_id)
        if self._repository.get_prescription_for_visit(visit_id) is not None:
            raise HealthLinkError(
                "A prescription already exists for this visit; use PUT "
                "to update it.",
                status_code=409,
            )
        _validate_payload_text(
            payload.diagnostic_information,
            payload.medical_advice,
            payload.notes,
            payload.items,
        )
        prescription = Prescription(
            id=uuid.uuid4(),
            visit_id=visit_id,
            citizen_id=visit.citizen_id,
            author_doctor_role_registration_id=doctor_role_registration_id,
            diagnostic_information=payload.diagnostic_information,
            medical_advice=payload.medical_advice,
            notes=payload.notes,
            items=_materialise_items(payload.items),
        )
        self._db.add(prescription)
        self._db.flush()
        return self._commit_with_best_effort_pdf(prescription)

    def update(
        self,
        doctor_role_registration_id: uuid.UUID,
        prescription_id: uuid.UUID,
        payload: PrescriptionUpdateRequest,
    ) -> PrescriptionView:
        prescription = self._repository.get_prescription_by_id(prescription_id)
        if prescription is None:
            raise HealthLinkError(
                "Prescription not found.", status_code=404
            )
        if (
            prescription.author_doctor_role_registration_id
            != doctor_role_registration_id
        ):
            raise HealthLinkError(
                "Only the author doctor may edit this prescription.",
                status_code=403,
            )
        visit = self._repository.get_visit_for_prescription(prescription)
        if visit is None:
            raise HealthLinkError(
                "Underlying medical visit could not be resolved.",
                status_code=404,
            )
        _ensure_visit_doctor_owns_visit(visit, doctor_role_registration_id)
        _validate_payload_text(
            payload.diagnostic_information,
            payload.medical_advice,
            payload.notes,
            payload.items,
        )

        prescription.diagnostic_information = payload.diagnostic_information
        prescription.medical_advice = payload.medical_advice
        prescription.notes = payload.notes
        self._repository.replace_items(
            prescription, _materialise_items(payload.items)
        )
        return self._commit_with_best_effort_pdf(prescription)

    # ---- pdf streaming ------------------------------------------------

    def stream_pdf(
        self,
        prescription_id: uuid.UUID,
    ) -> tuple[bytes, str]:
        prescription = self._repository.get_prescription_by_id(prescription_id)
        if prescription is None:
            raise HealthLinkError(
                "Prescription not found.", status_code=404
            )
        document = prescription.document
        if document is None:
            raise HealthLinkError(
                "Prescription PDF has not been generated yet.",
                status_code=404,
            )
        if not self._storage.exists(document.storage_key):
            raise HealthLinkError(
                "Prescription PDF is not currently available; ask the "
                "doctor to regenerate.",
                status_code=410,
            )
        return self._storage.load(document.storage_key), document.file_name


__all__ = [
    "PrescriptionsService",
    "_prescription_view",
]
