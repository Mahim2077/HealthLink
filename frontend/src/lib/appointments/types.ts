// Phase 10 frontend types mirror backend/app/appointments/schemas.py.
// These shapes are intentionally PII-safe: doctor identity is reduced to the
// fields surfaced by the citizen booking endpoints; no BMDC numbers or
// professional contact details leak through here.

import type { ChamberAppointmentView } from "@/lib/chamber/types";

export type AppointmentStatus =
  | "BOOKED"
  | "CANCELLED"
  | "COMPLETED"
  | "REMOVED_BY_DOCTOR"
  | "NO_SHOW";

export const APPOINTMENT_STATUSES: AppointmentStatus[] = [
  "BOOKED",
  "CANCELLED",
  "COMPLETED",
  "REMOVED_BY_DOCTOR",
  "NO_SHOW",
];

export type QueueStatus =
  | "WAITING"
  | "CURRENT"
  | "SKIPPED"
  | "DONE"
  | "REMOVED"
  | "CANCELLED";

export type AppointmentBookingRequest = {
  doctor_user_id: string;
  facility_id: string;
  appointment_date: string;
  reason?: string | null;
};

export type AppointmentQueueEntryView = {
  id: string;
  queue_status: QueueStatus;
  became_current_at: string | null;
  finished_at: string | null;
  removed_at: string | null;
};

export type AppointmentBookingResponse = {
  id: string;
  citizen_id: string;
  doctor_role_registration_id: string;
  doctor_user_id: string;
  facility_id: string;
  facility_name: string;
  appointment_date: string;
  serial_number: number;
  status: AppointmentStatus;
  reason: string | null;
  booked_at: string;
  queue: AppointmentQueueEntryView;
};

export type AppointmentListEntry = {
  id: string;
  doctor_user_id: string;
  doctor_name: string;
  facility_id: string;
  facility_name: string;
  appointment_date: string;
  serial_number: number;
  status: AppointmentStatus;
  booked_at: string;
  cancelled_at: string | null;
  completed_at: string | null;
  prescription_id: string | null;
};

export type AppointmentListResponse = {
  appointments: AppointmentListEntry[];
};

export type AppointmentFinishResponse = {
  appointment_id: string;
  visit_id: string;
  queue_id: string;
  serial_number: number;
  appointment_status: "COMPLETED";
  queue_status: "DONE";
  visit_status: "FINALIZED";
  completed_at: string;
  finished_at: string;
  finalized_at: string;
  next_current: ChamberAppointmentView | null;
};
