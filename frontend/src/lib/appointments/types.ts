// Phase 10 frontend types mirror backend/app/appointments/schemas.py.
// These shapes are intentionally PII-safe: doctor identity is reduced to the
// fields surfaced by the citizen booking endpoints; no BMDC numbers or
// professional contact details leak through here.

export type AppointmentStatus =
  | "BOOKED"
  | "CANCELLED"
  | "COMPLETED";

export const APPOINTMENT_STATUSES: AppointmentStatus[] = [
  "BOOKED",
  "CANCELLED",
  "COMPLETED",
];

export type QueueStatus =
  | "WAITING"
  | "CURRENT"
  | "DONE"
  | "REMOVED";

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
};

export type AppointmentListResponse = {
  appointments: AppointmentListEntry[];
};
