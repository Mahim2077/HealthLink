import type { AccessTokenResponse } from "@/lib/auth/types";

export type AdminLoginRequest = {
  email: string;
  password: string;
};

export type AdminLoginResponse = AccessTokenResponse & {
  portal: "ADMIN";
};

export type AdminMe = {
  user_id: string;
  admin_id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_super_admin: boolean;
};

export type FacilityType = "HOSPITAL" | "CLINIC" | "DIAGNOSTIC_CENTER" | "PHARMACY";

export type Facility = {
  id: string;
  name: string;
  facility_type: FacilityType;
  registration_number: string | null;
  address: string;
  phone: string | null;
  email: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type FacilityWriteRequest = Omit<Facility, "id" | "created_at" | "updated_at">;

export type VerificationStatus = "PENDING" | "VERIFIED" | "REJECTED";

export type ProfessionalRegistrationSummary = {
  id: string;
  professional_id: string;
  user_id: string;
  first_name: string;
  last_name: string;
  email: string;
  role_code: string;
  role_name: string;
  facility_name_submitted: string;
  designation: string;
  verification_status: VerificationStatus;
  submitted_at: string;
};

export type ProfessionalRegistrationDetail = ProfessionalRegistrationSummary & {
  additional_info: string | null;
  bmdc_registration_number: string | null;
  facility: Facility | null;
  verified_at: string | null;
  verified_by: string | null;
  rejected_at: string | null;
  rejection_reason: string | null;
};

export type CitizenRegistrationMethod = "NID" | "BCN";

export type CitizenIdentitySummary = {
  user_id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  registered_with: CitizenRegistrationMethod;
  nid_number: string | null;
  birth_certificate_number: string | null;
  nid_added_at: string | null;
  identity_created_at: string;
  identity_updated_at: string;
};

export type CitizenIdentityDetail = CitizenIdentitySummary & {
  national_identifier_id: string | null;
  national_identifier_created_at: string | null;
  date_of_birth: string | null;
  gender: string | null;
  blood_group: string | null;
  address: string | null;
  auth_session_count: number;
  created_at: string;
  updated_at: string;
};

export type CitizenIdentityCorrectionType = "NID" | "BCN";

export type CitizenIdentityCorrectionRequest = {
  correction_type: CitizenIdentityCorrectionType;
  new_value: string;
  reason: string;
};

export type CitizenIdentityCorrectionResponse = {
  user_id: string;
  correction_type: CitizenIdentityCorrectionType;
  previous_value: string | null;
  new_value: string;
  corrected_at: string;
  audit_log_id: string;
};
