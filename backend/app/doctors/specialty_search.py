"""Explicit discovery aliases, not fuzzy interpretation of medical symptoms."""

from app.professionals.constants import DOCTOR_SPECIALIZATION_LABELS, DoctorSpecialization


SPECIALTY_SEARCH_ALIASES: dict[DoctorSpecialization, tuple[str, ...]] = {
    DoctorSpecialization.GENERAL_MEDICINE: ("general physician", "general practitioner", "gp"),
    DoctorSpecialization.INTERNAL_MEDICINE: ("internist", "internal medicine specialist"),
    DoctorSpecialization.PEDIATRICS: ("pediatrician", "pediatricians", "paediatrician", "paediatricians", "paediatrics", "child specialist"),
    DoctorSpecialization.CARDIOLOGY: ("cardiologist", "cardiologists", "heart specialist"),
    DoctorSpecialization.ORTHOPEDICS: ("orthopedist", "orthopedists", "orthopaedist", "orthopaedics", "orthopedic surgeon", "orthopaedic surgeon"),
    DoctorSpecialization.DERMATOLOGY: ("dermatologist", "dermatologists", "skin specialist"),
    DoctorSpecialization.GYNECOLOGY_OBSTETRICS: ("gynecology", "gynaecology", "gynecologist", "gynaecologist", "obstetrics", "obstetrician"),
    DoctorSpecialization.NEUROLOGY: ("neurologist", "neurologists"),
    DoctorSpecialization.PSYCHIATRY: ("psychiatrist", "psychiatrists"),
    DoctorSpecialization.ENT: ("ent specialist", "otolaryngologist", "ear nose throat", "ear nose and throat"),
    DoctorSpecialization.OPHTHALMOLOGY: ("ophthalmologist", "ophthalmologists", "eye specialist"),
    DoctorSpecialization.GENERAL_SURGERY: ("general surgeon", "general surgeons"),
    DoctorSpecialization.ENDOCRINOLOGY: ("endocrinologist", "endocrinologists"),
    DoctorSpecialization.GASTROENTEROLOGY: ("gastroenterologist", "gastroenterologists"),
    DoctorSpecialization.NEPHROLOGY: ("nephrologist", "nephrologists", "kidney specialist"),
    DoctorSpecialization.ONCOLOGY: ("oncologist", "oncologists", "cancer specialist"),
    DoctorSpecialization.PULMONOLOGY: ("pulmonologist", "pulmonologists", "lung specialist"),
    DoctorSpecialization.UROLOGY: ("urologist", "urologists"),
}


def _normalize(query: str) -> str:
    return " ".join(query.casefold().replace("_", " ").replace("-", " ").replace("&", " and ").split())


def specialty_codes_for_query(query: str) -> tuple[str, ...]:
    """Match whole known terms; symptoms and arbitrary near-spellings are not aliases."""
    normalized = _normalize(query)
    return tuple(
        specialty.value
        for specialty, aliases in SPECIALTY_SEARCH_ALIASES.items()
        if normalized in {
            _normalize(specialty.value),
            _normalize(DOCTOR_SPECIALIZATION_LABELS[specialty]),
            *(_normalize(alias) for alias in aliases),
        }
    )
