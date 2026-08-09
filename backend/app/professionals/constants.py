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
