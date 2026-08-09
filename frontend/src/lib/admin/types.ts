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
