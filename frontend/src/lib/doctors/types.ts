// Phase 9 frontend types mirror backend/app/doctors/schemas.py.
// These shapes are intentionally PII-safe: nid_number, bmdc_registration_number,
// and other sensitive identifiers are not surfaced to the citizen portal.

export type PracticeWeekday =
  | "MONDAY"
  | "TUESDAY"
  | "WEDNESDAY"
  | "THURSDAY"
  | "FRIDAY"
  | "SATURDAY"
  | "SUNDAY";

export const PRACTICE_WEEKDAYS: PracticeWeekday[] = [
  "MONDAY",
  "TUESDAY",
  "WEDNESDAY",
  "THURSDAY",
  "FRIDAY",
  "SATURDAY",
  "SUNDAY",
];

export type PracticeScheduleStatus = "ACTIVE" | "INACTIVE";

export type DoctorSummary = {
  id: string;
  name: string;
  first_name: string;
  last_name: string;
  facility_id: string;
  facility_name: string;
  facility_type: string;
  designation: string;
  role_code: string;
  verified: boolean;
  specialization: string | null;
};

export type PracticeDay = {
  id: string;
  facility_id: string;
  facility_name: string;
  weekday: PracticeWeekday;
  start_time: string;
  end_time: string;
  max_patients: number;
  status: PracticeScheduleStatus;
};

export type DoctorProfile = DoctorSummary & {
  email: string;
  verified_at: string | null;
  submitted_at: string;
  practice_days: PracticeDay[];
};

export type PracticeScheduleEntry = {
  id: string;
  facility_id: string;
  facility_name: string;
  weekday: PracticeWeekday;
  start_time: string;
  end_time: string;
  max_patients: number;
  status: PracticeScheduleStatus;
  created_at: string;
  updated_at: string;
};

export type PracticeScheduleWriteRequest = {
  facility_id: string;
  weekday: PracticeWeekday;
  start_time: string;
  end_time: string;
  max_patients: number;
  status: PracticeScheduleStatus;
};

export type PracticeScheduleCreateResponse = {
  schedule: PracticeScheduleEntry;
};

export type PracticeScheduleDeleteResponse = {
  id: string;
  deleted_at: string;
};

export type DoctorSearchFilters = {
  name?: string;
  facility_name?: string;
  weekday?: PracticeWeekday;
  limit?: number;
};

export type FacilityChoice = {
  id: string;
  name: string;
  facility_type: string;
  is_active: boolean;
  is_verified_assignment: boolean;
};