"use client";

import { apiClient } from "@/lib/api/client";

export type RecentPrescription = { id: string; created_at: string };
export type CitizenOverview = {
  today: string;
  upcoming_appointment: { id: string; appointment_date: string; facility_name: string; serial_number: number } | null;
  recent_prescription: RecentPrescription | null;
  latest_report: { diagnostic_test_id: string; test_name: string; report_date: string } | null;
  active_reminders: number;
  unread_notifications: number;
  emergency_profile_updated_at: string | null;
};
export type ProfessionalOverview = {
  today: string;
  role_code: "DOCTOR" | "LAB_TECHNICIAN";
  chambers: { facility_name: string; status: string; waiting_count: number; current_serial: number | null }[];
  chambers_has_more: boolean;
  requested_tests: number;
  in_progress_tests: number;
  draft_reports: number;
  finalized_reports: number;
  recent_prescription: RecentPrescription | null;
};
export type AdminOverview = { pending_professional_registrations: number; active_facilities: number; facilities_needing_location: number };

export const loadCitizenOverview = () => apiClient.get<CitizenOverview>("citizens/me/overview");
export const loadProfessionalOverview = () => apiClient.get<ProfessionalOverview>("professionals/me/overview");
export const loadAdminOverview = () => apiClient.get<AdminOverview>("admin/overview");
