export type DiagnosticStatus = "REQUESTED" | "IN_PROGRESS" | "COMPLETED" | "CANCELLED";
export type DiagnosticTest = { id: string; citizen_id: string; visit_id: string | null; requested_by_role_registration_id: string; assigned_to_role_registration_id: string | null; facility_id: string | null; facility_name: string | null; test_name: string; instructions: string | null; status: DiagnosticStatus; requested_by_name: string; assigned_to_name: string | null; created_at: string; updated_at: string };
export type DiagnosticTestList = { tests: DiagnosticTest[] };
export type TechnicianChoice = { role_registration_id: string; full_name: string; designation: string; facility_id: string; facility_name: string };
