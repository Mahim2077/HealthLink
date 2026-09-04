// Phase 12 frontend types mirror backend/app/visits/schemas.py.
// Two projections live here:
//   - the doctor`s consultation workspace (DraftView + current patient);
//   - the citizen read path (today`s own visits + single visit detail).

export type VisitStatus = "DRAFT" | "FINALIZED";

export type VisitAccessSource = "queue" | "grant" | "citizen";

export type PatientSummary = {
  citizen_id: string;
  full_name: string;
  date_of_birth: string | null;
  gender: string | null;
  blood_group: string | null;
  age_years: number | null;
};

export type VisitDraftView = {
  id: string;
  citizen_id: string;
  doctor_role_registration_id: string;
  facility_id: string;
  appointment_id: string | null;
  prescription_id: string | null;
  visit_date: string;
  chief_complaint: string | null;
  clinical_notes: string | null;
  diagnosis: string | null;
  follow_up_instructions: string | null;
  status: VisitStatus;
  finalized_at: string | null;
  updated_at: string;
  patient: PatientSummary | null;
  access_source: VisitAccessSource;
};

export type VisitDraftUpdateRequest = {
  chief_complaint?: string | null;
  clinical_notes?: string | null;
  diagnosis?: string | null;
  follow_up_instructions?: string | null;
};

export type DoctorCurrentPatientView = {
  queue_id: string;
  appointment_id: string;
  serial_number: number;
  citizen_id: string;
  facility_id: string;
  facility_name: string;
  patient: PatientSummary;
  visit: VisitDraftView | null;
};

export type CitizenVisitSummary = {
  id: string;
  doctor_user_id: string;
  doctor_name: string;
  facility_id: string;
  facility_name: string;
  appointment_id: string | null;
  prescription_id: string | null;
  serial_number: number | null;
  visit_date: string;
  status: VisitStatus;
  finalized_at: string | null;
  chief_complaint: string | null;
  diagnosis: string | null;
  follow_up_instructions: string | null;
};

export type CitizenVisitListResponse = {
  visits: CitizenVisitSummary[];
};

export function describeVisitStatus(status: VisitStatus): string {
  switch (status) {
    case "DRAFT":
      return "In progress";
    case "FINALIZED":
      return "Closed";
  }
}

export function badgeClassForVisit(status: VisitStatus): string {
  switch (status) {
    case "DRAFT":
      return "bg-amber-50 text-amber-800";
    case "FINALIZED":
      return "bg-emerald-50 text-emerald-700";
  }
}

export function isFinalized(visit: VisitDraftView | null | undefined): boolean {
  return visit?.status === "FINALIZED";
}
