from enum import StrEnum


class ProfessionalRoleCode(StrEnum):
    DOCTOR = "DOCTOR"
    LAB_TECHNICIAN = "LAB_TECHNICIAN"
    NURSE = "NURSE"
    PHARMACIST = "PHARMACIST"
    RADIOLOGY_TECHNICIAN = "RADIOLOGY_TECHNICIAN"
    OTHER_HEALTHCARE_PROFESSIONAL = "OTHER_HEALTHCARE_PROFESSIONAL"


class VerificationStatus(StrEnum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class DoctorSpecialization(StrEnum):
    GENERAL_MEDICINE = "GENERAL_MEDICINE"
    INTERNAL_MEDICINE = "INTERNAL_MEDICINE"
    PEDIATRICS = "PEDIATRICS"
    CARDIOLOGY = "CARDIOLOGY"
    ORTHOPEDICS = "ORTHOPEDICS"
    DERMATOLOGY = "DERMATOLOGY"
    GYNECOLOGY_OBSTETRICS = "GYNECOLOGY_OBSTETRICS"
    NEUROLOGY = "NEUROLOGY"
    PSYCHIATRY = "PSYCHIATRY"
    ENT = "ENT"
    OPHTHALMOLOGY = "OPHTHALMOLOGY"
    GENERAL_SURGERY = "GENERAL_SURGERY"
    ENDOCRINOLOGY = "ENDOCRINOLOGY"
    GASTROENTEROLOGY = "GASTROENTEROLOGY"
    NEPHROLOGY = "NEPHROLOGY"
    ONCOLOGY = "ONCOLOGY"
    PULMONOLOGY = "PULMONOLOGY"
    UROLOGY = "UROLOGY"


DOCTOR_SPECIALIZATION_LABELS: dict[DoctorSpecialization, str] = {
    DoctorSpecialization.GENERAL_MEDICINE: "General Medicine",
    DoctorSpecialization.INTERNAL_MEDICINE: "Internal Medicine",
    DoctorSpecialization.PEDIATRICS: "Pediatrics",
    DoctorSpecialization.CARDIOLOGY: "Cardiology",
    DoctorSpecialization.ORTHOPEDICS: "Orthopedics",
    DoctorSpecialization.DERMATOLOGY: "Dermatology",
    DoctorSpecialization.GYNECOLOGY_OBSTETRICS: "Gynecology & Obstetrics",
    DoctorSpecialization.NEUROLOGY: "Neurology",
    DoctorSpecialization.PSYCHIATRY: "Psychiatry",
    DoctorSpecialization.ENT: "ENT",
    DoctorSpecialization.OPHTHALMOLOGY: "Ophthalmology",
    DoctorSpecialization.GENERAL_SURGERY: "General Surgery",
    DoctorSpecialization.ENDOCRINOLOGY: "Endocrinology",
    DoctorSpecialization.GASTROENTEROLOGY: "Gastroenterology",
    DoctorSpecialization.NEPHROLOGY: "Nephrology",
    DoctorSpecialization.ONCOLOGY: "Oncology",
    DoctorSpecialization.PULMONOLOGY: "Pulmonology",
    DoctorSpecialization.UROLOGY: "Urology",
}


ROLE_SEED_DATA: tuple[tuple[ProfessionalRoleCode, str, str], ...] = (
    (ProfessionalRoleCode.DOCTOR, "Doctor", "Registered medical doctor"),
    (
        ProfessionalRoleCode.LAB_TECHNICIAN,
        "Lab Technician",
        "Diagnostic laboratory professional",
    ),
    (ProfessionalRoleCode.NURSE, "Nurse", "Nursing professional"),
    (ProfessionalRoleCode.PHARMACIST, "Pharmacist", "Pharmacy professional"),
    (
        ProfessionalRoleCode.RADIOLOGY_TECHNICIAN,
        "Radiology Technician",
        "Radiology and imaging professional",
    ),
    (
        ProfessionalRoleCode.OTHER_HEALTHCARE_PROFESSIONAL,
        "Other Healthcare Professional",
        "Other healthcare professional role",
    ),
)
