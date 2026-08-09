export const PROFESSIONAL_ROLES = [
  { code: "DOCTOR", name: "Doctor" },
  { code: "LAB_TECHNICIAN", name: "Lab Technician" },
  { code: "NURSE", name: "Nurse" },
  { code: "PHARMACIST", name: "Pharmacist" },
  { code: "RADIOLOGY_TECHNICIAN", name: "Radiology Technician" },
  {
    code: "OTHER_HEALTHCARE_PROFESSIONAL",
    name: "Other Healthcare Professional",
  },
] as const;

export type ProfessionalRoleCode = (typeof PROFESSIONAL_ROLES)[number]["code"];

type ProfessionalApplicationBase = {
  role_code: ProfessionalRoleCode;
  facility_name: string;
  designation: string;
  additional_info: string;
};

export type ProfessionalApplicationFields =
  | (ProfessionalApplicationBase & {
      role_code: "DOCTOR";
      bmdc_registration_number: string;
    })
  | (ProfessionalApplicationBase & {
      role_code: Exclude<ProfessionalRoleCode, "DOCTOR">;
      bmdc_registration_number?: never;
    });

export type ProfessionalRegistrationRequest = ProfessionalApplicationFields & {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  nid_number: string;
};

export type ProfessionalOnboardingRequest = ProfessionalApplicationFields;

export type ProfessionalApplicationResponse = {
  user_id: string;
  professional_id: string;
  role_registration_id: string;
  role_code: ProfessionalRoleCode;
  verification_status: "PENDING";
  submitted_at: string;
};
