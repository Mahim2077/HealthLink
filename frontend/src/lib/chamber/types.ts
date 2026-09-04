// Phase 11 frontend types mirror backend/app/appointments/schemas.py.
// These shapes are intentionally narrow: only the chamber view the
// verified doctor needs on the doctor-portal side is exposed. The
// citizen-facing projection lives in lib/appointments instead.

export type AppointmentStatus =
  | "BOOKED"
  | "CANCELLED"
  | "COMPLETED"
  | "REMOVED_BY_DOCTOR"
  | "NO_SHOW";

export type QueueStatus =
  | "WAITING"
  | "CURRENT"
  | "SKIPPED"
  | "DONE"
  | "REMOVED"
  | "CANCELLED";

export type SessionStatus = "NOT_STARTED" | "ACTIVE" | "COMPLETED";

export type ChamberAppointmentView = {
  queue_id: string;
  appointment_id: string;
  serial_number: number;
  status: AppointmentStatus;
  queue_status: QueueStatus;
  reason: string | null;
  booked_at: string;
  became_current_at: string | null;
  finished_at: string | null;
  removed_at: string | null;
};

export type ChamberSessionView = {
  id: string;
  facility_id: string;
  facility_name: string;
  session_date: string;
  status: SessionStatus;
  started_at: string | null;
  ended_at: string | null;
  current: ChamberAppointmentView | null;
  waiting: ChamberAppointmentView[];
  finished: ChamberAppointmentView[];
};

export type ChamberQueueActionResponse = {
  queue_id: string;
  appointment_id: string;
  serial_number: number;
  queue_status: QueueStatus;
  appointment_status: AppointmentStatus;
  became_current_at: string | null;
  finished_at: string | null;
  removed_at: string | null;
  next_current: ChamberAppointmentView | null;
};

export type ChamberSessionFinishResponse = {
  id: string;
  facility_id: string;
  session_date: string;
  status: SessionStatus;
  started_at: string | null;
  ended_at: string | null;
  remaining_waiting: number;
};

export type ChamberSessionStartRequest = {
  facility_id: string;
  session_date: string;
};

export type ChamberQueueActionName =
  | "call-next"
  | "skip"
  | "remove"
  | "no-show";

// Human-readable label for the queue_status badge.
export function describeQueueStatus(status: QueueStatus): string {
  switch (status) {
    case "WAITING":
      return "Waiting";
    case "CURRENT":
      return "With doctor";
    case "DONE":
      return "Completed";
    case "SKIPPED":
      return "Skipped";
    case "REMOVED":
      return "Removed";
    case "CANCELLED":
      return "Cancelled";
  }
}

export function describeSessionStatus(status: SessionStatus): string {
  switch (status) {
    case "NOT_STARTED":
      return "Not started";
    case "ACTIVE":
      return "In progress";
    case "COMPLETED":
      return "Closed for the day";
  }
}
