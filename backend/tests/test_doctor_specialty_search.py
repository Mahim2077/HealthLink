import pytest

from app.doctors.specialty_search import SPECIALTY_SEARCH_ALIASES, specialty_codes_for_query
from app.professionals.constants import DOCTOR_SPECIALIZATION_LABELS, DoctorSpecialization


@pytest.mark.parametrize("specialty", list(DoctorSpecialization))
def test_specialty_search_accepts_codes_labels_and_explicit_aliases(specialty) -> None:
    for term in (specialty.value, DOCTOR_SPECIALIZATION_LABELS[specialty], *SPECIALTY_SEARCH_ALIASES[specialty]):
        assert specialty.value in specialty_codes_for_query(term)


def test_specialty_search_normalizes_common_word_separators_and_case() -> None:
    assert specialty_codes_for_query("  HEART   specialist ") == ("CARDIOLOGY",)
    assert specialty_codes_for_query("Orthopaedic-Surgeon") == ("ORTHOPEDICS",)
    assert specialty_codes_for_query("Gynecology & Obstetrics") == ("GYNECOLOGY_OBSTETRICS",)


@pytest.mark.parametrize("query", ["chest pain", "cardiolog", "not a cardiologist", "", "surgery advice"])
def test_specialty_search_does_not_interpret_symptoms_or_arbitrary_phrases(query) -> None:
    assert specialty_codes_for_query(query) == ()
