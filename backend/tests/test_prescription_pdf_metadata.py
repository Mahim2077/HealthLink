"""Historical PDF metadata is derived from the encounter, not regeneration time."""
from datetime import UTC, date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.prescriptions.models import PrescriptionDocument
from app.prescriptions.pdf import _patient_block, _styles, bangladesh_visit_time
from app.prescriptions.service import PrescriptionsService
from test_medical_history import _citizen, _facility, _prescription, _professional, _visit


@pytest.mark.parametrize(
    ("visit_time", "dob", "expected_age", "expected_date"),
    [
        (datetime(2019, 12, 31, 17, 59, tzinfo=UTC), date(2000, 1, 1),
         "19 years (DOB 2000-01-01)", "2019-12-31 23:59 Bangladesh time"),
        (datetime(2019, 12, 31, 18, 0, tzinfo=UTC), date(2000, 1, 1),
         "20 years (DOB 2000-01-01)", "2020-01-01 00:00 Bangladesh time"),
        (datetime(2019, 12, 31, 18, 0), date(2000, 1, 1),
         "20 years (DOB 2000-01-01)", "2020-01-01 00:00 Bangladesh time"),
        (datetime(2019, 12, 31, 18, 0, tzinfo=UTC), date(2020, 1, 2),
         "Age unavailable at visit (DOB 2020-01-02)", "2020-01-01 00:00 Bangladesh time"),
    ],
)
def test_regenerated_pdf_uses_encounter_age_date_and_facility(
    db_session, monkeypatch, visit_time, dob, expected_age, expected_date
):
    facility = _facility(db_session)
    _, author = _professional(db_session, facility)
    citizen = _citizen(db_session, "Historical")
    citizen.date_of_birth = dob
    visit = _visit(
        db_session, citizen=citizen, registration=author, facility=facility,
        finalized_at=datetime(2020, 1, 1, tzinfo=UTC), diagnosis="Historical care",
    )
    visit.visit_date = visit_time
    prescription = _prescription(
        db_session, visit=visit, registration=author,
        created_at=datetime(2020, 1, 1, tzinfo=UTC),
    )
    db_session.commit()
    # Exercise the database's naive-UTC return convention, not only cached rows.
    db_session.expire_all()
    captured = []

    def render(view):
        captured.append(view)
        return b"%PDF-historical-metadata"

    monkeypatch.setattr("app.prescriptions.service.generate_prescription_pdf_bytes", render)
    service = PrescriptionsService(db_session)
    before, filename = service.stream_pdf(prescription.id)
    assert before == b"%PDF-historical-metadata"

    reassigned = _facility(db_session)
    reassigned.name = "New assignment, not the encounter facility"
    author.facility_id = reassigned.id
    author.facility_name_submitted = reassigned.name
    db_session.commit()
    db_session.expire_all()
    after, regenerated_filename = service.stream_pdf(prescription.id)
    assert after == before
    assert regenerated_filename == filename
    assert len(captured) == 2
    for view in captured:
        assert view.doctor.facility_name == facility.name
        assert view.doctor.facility_name != reassigned.name
        assert view.patient_age == expected_age
        # Inspect the actual text supplied to the unchanged PDF patient table.
        rows = _patient_block(_styles(), view)[0]._cellvalues
        assert rows[1][1].getPlainText() == expected_age
        assert rows[3][1].getPlainText() == expected_date
    assert db_session.scalar(select(PrescriptionDocument)) is None


def test_bangladesh_visit_time_normalizes_aware_and_naive_utc_equally():
    local_midnight = datetime(2020, 1, 1, tzinfo=timezone(timedelta(hours=6)))
    utc = datetime(2019, 12, 31, 18, tzinfo=UTC)
    naive_utc = datetime(2019, 12, 31, 18)
    assert bangladesh_visit_time(local_midnight) == local_midnight
    assert bangladesh_visit_time(utc) == local_midnight
    assert bangladesh_visit_time(naive_utc) == local_midnight
