"""Create new synthetic browser fixtures in the hard-coded loopback QA DB only."""
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
import json
import re
import sys

root = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(root / "backend"), str(root / "backend/tests")]
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.main import create_app  # register models, without connecting
from app.admins.models import AdminAccount
from app.auth.models import User
from app.citizens.models import CitizenIdentifier, UserNationalIdentifier
from app.core.security import hash_password
from app.dashboards.service import care_today
from app.db.session import create_database_engine
from app.diagnostics.models import DiagnosticTest
from app.diagnostics.report_models import LabReport, LabReportItem
from app.doctors.models import DoctorPracticeSchedule
from app.emergency.models import EmergencyProfile
from app.locations.service import list_area_options, resolve_area
from app.professionals.constants import ProfessionalRoleCode
from app.professionals.models import DoctorRegistrationDetail
from test_diagnostics import _citizen, _facility, _registration, _user
from test_medical_history import _prescription, _visit

run_id = sys.argv[1]
if not re.fullmatch(r"\d{13}", run_id):
    raise RuntimeError("A unique synthetic millisecond run ID is required.")
password = "LocalOnly-BrowserQA-Test123!"
url = "postgresql+psycopg://postgres@127.0.0.1:55433/healthlink_phase27_qa"
with Session(create_database_engine(url)) as db:
    if db.scalar(select(User).where(User.email == f"browser-citizen-{run_id}@example.com")):
        raise RuntimeError("Never overwrite existing browser fixtures.")
    facility = _facility(db, f"Synthetic Browser Hospital {run_id[-6:]}")
    areas = list_area_options()
    district = next(item for item in areas.districts if item.name == "Dhaka")
    upazila = next(item for item in areas.upazilas if item.district_code == district.code)
    _, place = resolve_area(district.code, upazila.code)
    facility.address = f"Synthetic local test address, {upazila.name}, Dhaka"
    facility.district_code, facility.upazila_code = district.code, upazila.code
    facility.latitude, facility.longitude = place.point.latitude, place.point.longitude
    facility.location_status = "CONFIRMED"
    doctor_user, doctor = _registration(db, facility, ProfessionalRoleCode.DOCTOR)
    lab_user, lab = _registration(db, facility, ProfessionalRoleCode.LAB_TECHNICIAN)
    previous_user, previous_doctor = _registration(db, facility, ProfessionalRoleCode.DOCTOR)
    pending_user, pending_doctor = _registration(db, facility, ProfessionalRoleCode.DOCTOR, verified=False)
    citizen_user, citizen = _citizen(db, "Browser")
    other_user, other_citizen = _citizen(db, "OtherBrowser")
    admin_user = _user(db, "BrowserAdmin")
    for label, user in [("doctor", doctor_user), ("lab", lab_user), ("citizen", citizen_user),
                        ("other", other_user), ("admin", admin_user), ("pending", pending_user)]:
        user.email = f"browser-{label}-{run_id}@example.com"
        user.password_hash = hash_password(password)
    doctor_user.first_name, doctor_user.last_name = "BrowserDoctor", run_id[-6:]
    previous_user.first_name, previous_user.last_name = "PreviousDoctor", run_id[-6:]
    pending_user.first_name, pending_user.last_name = "PendingDoctor", run_id[-6:]
    citizen_user.last_name = f"Citizen{run_id[-6:]}"
    citizen.address = "Synthetic QA address only"
    doctor_nid, lab_nid = "99" + run_id[-8:], "98" + run_id[-8:]
    db.add_all([UserNationalIdentifier(user_id=doctor_user.id, nid_number=doctor_nid),
                UserNationalIdentifier(user_id=lab_user.id, nid_number=lab_nid),
                AdminAccount(user_id=admin_user.id),
                CitizenIdentifier(user_id=citizen_user.id, registered_with="BCN", birth_certificate_number="7000" + run_id),
                CitizenIdentifier(user_id=other_user.id, registered_with="BCN", birth_certificate_number="7100" + run_id)])
    for registration in (doctor, previous_doctor, pending_doctor):
        db.add(DoctorRegistrationDetail(professional_role_registration_id=registration.id,
            bmdc_registration_number=f"LOCAL-QA-{registration.id}", specialization="GENERAL_MEDICINE", qualification="Synthetic qualification"))
    today = care_today()
    schedule = DoctorPracticeSchedule(doctor_user_id=doctor_user.id, facility_id=facility.id,
        weekday=today.strftime("%A").upper(), start_time=time(0, 0), end_time=time(23, 59),
        max_patients=20, status="ACTIVE")
    db.add(schedule)
    db.commit()
    past = datetime.now(UTC) - timedelta(days=2)
    visit = _visit(db, citizen=citizen, registration=previous_doctor, facility=facility,
        finalized_at=past, diagnosis="Synthetic recorded condition")
    prescription = _prescription(db, visit=visit, registration=previous_doctor, created_at=past)
    diagnostic = DiagnosticTest(citizen_id=citizen.id, visit_id=visit.id,
        requested_by_role_registration_id=previous_doctor.id, assigned_to_role_registration_id=lab.id,
        facility_id=facility.id, test_name="Historical synthetic CBC", status="COMPLETED")
    db.add(diagnostic)
    db.flush()
    report = LabReport(diagnostic_test_id=diagnostic.id, citizen_id=citizen.id,
        facility_id=facility.id, created_by_role_registration_id=lab.id,
        report_date=today - timedelta(days=2), status="FINALIZED", finalized_at=past,
        summary="Historical synthetic local result")
    db.add(report)
    db.flush()
    db.add(LabReportItem(lab_report_id=report.id, parameter_name="Haemoglobin", result_value_text="13.2",
        result_value_numeric="13.2", unit="g/dL", reference_range="12–16", flag="NORMAL"))
    db.add(EmergencyProfile(citizen_id=citizen.id, allergies="Synthetic recorded allergy", special_notes="Local test only"))
    db.commit()
    print(json.dumps({"run_id": run_id, "password": password,
        "citizen_email": citizen_user.email, "other_email": other_user.email,
        "admin_email": admin_user.email, "doctor_nid": doctor_nid, "lab_nid": lab_nid,
        "citizen_name": f"{citizen_user.first_name} {citizen_user.last_name}",
        "doctor_name": f"{doctor_user.first_name} {doctor_user.last_name}",
        "pending_name": f"{pending_user.first_name} {pending_user.last_name}",
        "facility_name": facility.name, "facility_id": str(facility.id), "doctor_id": str(doctor_user.id),
        "doctor_registration_id": str(doctor.id), "lab_registration_id": str(lab.id),
        "pending_registration_id": str(pending_doctor.id),
        "citizen_id": str(citizen.id), "citizen_user_id": str(citizen_user.id),
        "old_prescription_id": str(prescription.id),
        "old_test_id": str(diagnostic.id), "today": today.isoformat(),
        "district_code": district.code, "upazila_code": upazila.code,
        "district_name": district.name, "upazila_name": upazila.name,
        "schedule_id": str(schedule.id)}))
