from datetime import date

import pytest
from sqlalchemy import select

from app.auth.constants import Portal
from app.diagnostics.models import DiagnosticTest
from app.diagnostics.report_models import LabReport
from app.diagnostics.report_service import LabReportService
from app.professionals.constants import ProfessionalRoleCode
from test_diagnostics import _auth, _citizen, _facility, _queue, _registration, _token


@pytest.fixture
def report_case(db_session, test_settings):
    facility = _facility(db_session)
    doctor, registration = _registration(db_session, facility, ProfessionalRoleCode.DOCTOR)
    lab_user, lab = _registration(db_session, facility, ProfessionalRoleCode.LAB_TECHNICIAN)
    stranger, other_lab = _registration(db_session, facility, ProfessionalRoleCode.LAB_TECHNICIAN)
    citizen_user, citizen = _citizen(db_session, "Owner")
    other_citizen, _ = _citizen(db_session, "Other")
    visit = _queue(db_session, registration, facility, citizen)
    test = DiagnosticTest(citizen_id=citizen.id, visit_id=visit.id, requested_by_role_registration_id=registration.id, assigned_to_role_registration_id=lab.id, facility_id=facility.id, test_name="Blood count", status="IN_PROGRESS")
    db_session.add(test)
    db_session.commit()
    headers = {name: _auth(_token(db_session, test_settings, user, portal, role)) for name, user, portal, role in [
        ("lab", lab_user, Portal.PROFESSIONAL, lab), ("wrong_lab", stranger, Portal.PROFESSIONAL, other_lab),
        ("doctor", doctor, Portal.PROFESSIONAL, registration), ("citizen", citizen_user, Portal.CITIZEN, None),
        ("other_citizen", other_citizen, Portal.CITIZEN, None),
    ]}
    return test, lab, headers


def payload(unit="g/dL", report_date="2026-01-10"):
    return {"report_date": report_date, "summary": "Reviewed", "items": [{"parameter_name": "Haemoglobin", "result_value_text": "13.2", "result_value_numeric": "13.2", "unit": unit}]}


def test_report_authorization_draft_edit_and_immutable_finalization(client, db_session, report_case):
    test, _, headers = report_case
    path = f"/api/v1/diagnostic-tests/{test.id}/lab-report"
    for actor, status in [("wrong_lab", 404), ("doctor", 403), ("citizen", 403)]:
        assert client.put(path, headers=headers[actor], json=payload()).status_code == status
    assert client.get(path, headers=headers["lab"]).json() is None
    assert client.post(path + "/finalize", headers=headers["lab"]).status_code == 409
    assert client.put(path, headers=headers["lab"], json=payload()).status_code == 200
    updated = payload(); updated["summary"] = "Corrected draft"
    assert client.put(path, headers=headers["lab"], json=updated).json()["summary"] == "Corrected draft"
    for actor in ("citizen", "doctor", "wrong_lab", "other_citizen"):
        assert client.get(path, headers=headers[actor]).status_code == 404
    assert client.get("/api/v1/citizens/me/lab-reports", headers=headers["citizen"]).json() == []
    final = client.post(path + "/finalize", headers=headers["lab"])
    assert final.status_code == 200, final.text
    assert final.json()["status"] == "FINALIZED" and final.json()["finalized_at"]
    db_session.refresh(test)
    assert test.status == "COMPLETED"
    assert client.put(path, headers=headers["lab"], json=payload()).status_code == 409
    assert client.post(path + "/finalize", headers=headers["lab"]).status_code == 409
    for actor in ("citizen", "doctor", "lab"):
        assert client.get(path, headers=headers[actor]).status_code == 200
    assert client.get(path, headers=headers["other_citizen"]).status_code == 404


def test_finalize_rolls_back_both_records_on_commit_failure(client, db_session, report_case, monkeypatch):
    test, lab, headers = report_case
    path = f"/api/v1/diagnostic-tests/{test.id}/lab-report"
    assert client.put(path, headers=headers["lab"], json=payload()).status_code == 200
    def fail():
        db_session.flush()
        raise RuntimeError("Simulated commit failure")
    with monkeypatch.context() as patch:
        patch.setattr(db_session, "commit", fail)
        with pytest.raises(RuntimeError, match="Simulated"):
            LabReportService(db_session).finalize(test.id, lab)
    db_session.refresh(test)
    report = db_session.scalar(select(LabReport).where(LabReport.diagnostic_test_id == test.id))
    assert test.status == "IN_PROGRESS"
    assert report.status == "DRAFT" and report.finalized_at is None


def test_trends_include_only_final_numeric_results_preserve_units_and_order(client, db_session, report_case):
    test, _, headers = report_case
    for unit, report_date, finalize in [("g/dL", "2026-02-01", True), ("g/L", "2026-01-01", True), ("g/dL", "2026-03-01", False)]:
        row = DiagnosticTest(citizen_id=test.citizen_id, visit_id=test.visit_id, requested_by_role_registration_id=test.requested_by_role_registration_id, assigned_to_role_registration_id=test.assigned_to_role_registration_id, facility_id=test.facility_id, test_name="Repeat", status="IN_PROGRESS")
        db_session.add(row); db_session.commit()
        path = f"/api/v1/diagnostic-tests/{row.id}/lab-report"
        body = payload(unit, report_date)
        body["items"].append({"parameter_name": "Notes", "result_value_text": "Normal"})
        assert client.put(path, headers=headers["lab"], json=body).status_code == 200
        if finalize:
            assert client.post(path + "/finalize", headers=headers["lab"]).status_code == 200
    points = client.get("/api/v1/citizens/me/lab-trends", headers=headers["citizen"]).json()
    assert [(p["report_date"], p["unit"]) for p in points] == [("2026-01-01", "g/L"), ("2026-02-01", "g/dL")]
    assert client.get("/api/v1/citizens/me/lab-trends", headers=headers["other_citizen"]).json() == []


@pytest.mark.parametrize("value", ["NaN", "Infinity", "1000000000000", "1.1234567"])
def test_invalid_numeric_results_rejected(client, report_case, value):
    test, _, headers = report_case
    body = payload(); body["items"][0]["result_value_numeric"] = value
    assert client.put(f"/api/v1/diagnostic-tests/{test.id}/lab-report", headers=headers["lab"], json=body).status_code == 422
