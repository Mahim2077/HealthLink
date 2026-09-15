export const DOCTOR_SPECIALIZATIONS = [
  { code: "GENERAL_MEDICINE", label: "General Medicine" },
  { code: "INTERNAL_MEDICINE", label: "Internal Medicine" },
  { code: "PEDIATRICS", label: "Pediatrics" },
  { code: "CARDIOLOGY", label: "Cardiology" },
  { code: "ORTHOPEDICS", label: "Orthopedics" },
  { code: "DERMATOLOGY", label: "Dermatology" },
  { code: "GYNECOLOGY_OBSTETRICS", label: "Gynecology & Obstetrics" },
  { code: "NEUROLOGY", label: "Neurology" },
  { code: "PSYCHIATRY", label: "Psychiatry" },
  { code: "ENT", label: "ENT" },
  { code: "OPHTHALMOLOGY", label: "Ophthalmology" },
  { code: "GENERAL_SURGERY", label: "General Surgery" },
  { code: "ENDOCRINOLOGY", label: "Endocrinology" },
  { code: "GASTROENTEROLOGY", label: "Gastroenterology" },
  { code: "NEPHROLOGY", label: "Nephrology" },
  { code: "ONCOLOGY", label: "Oncology" },
  { code: "PULMONOLOGY", label: "Pulmonology" },
  { code: "UROLOGY", label: "Urology" },
] as const;

export type DoctorSpecialization = (typeof DOCTOR_SPECIALIZATIONS)[number]["code"];
