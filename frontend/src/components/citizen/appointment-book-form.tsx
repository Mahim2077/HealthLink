"use client";

import { useCallback, useState, type FormEvent } from "react";

import type { DoctorDiscoveryFacility, DoctorProfile } from "@/lib/doctors/types";
import { careDate } from "@/lib/care-date";
import { citizenErrorMessage } from "@/lib/citizen/presentation";
import { bookAppointment } from "@/lib/appointments/api";
import { facilityOptionLabels } from "@/lib/facilities/presentation";
import type {
  AppointmentBookingRequest,
  AppointmentBookingResponse,
} from "@/lib/appointments/types";

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

const REASON_MAX_LENGTH = 2000;

export type AppointmentBookFormValues = {
  doctorUserId: string;
  facilityId: string;
  appointmentDate: string;
  reason: string;
};

const todayIsoDate = careDate;

type BookingDoctor = Pick<DoctorProfile, "id" | "name" | "facility_id" | "facility_name" | "practice_days">;

/** The public facility catalog contains active facilities only. */
export function bookablePracticeFacilities(doctor: BookingDoctor, facilities: readonly DoctorDiscoveryFacility[]): DoctorDiscoveryFacility[] {
  const scheduled = new Set(doctor.practice_days.filter(day => day.status === "ACTIVE").map(day => day.facility_id));
  return facilities.filter(facility => scheduled.has(facility.id));
}

function appointmentWeekday(date: string): string | null {
  const parsed = new Date(`${date}T12:00:00Z`);
  return Number.isNaN(parsed.getTime()) ? null : new Intl.DateTimeFormat("en-US", { weekday: "long", timeZone: "UTC" }).format(parsed).toUpperCase();
}

export function validateAppointmentBooking(
  values: AppointmentBookFormValues,
): Partial<Record<keyof AppointmentBookFormValues, string>> {
  const errors: Partial<Record<keyof AppointmentBookFormValues, string>> = {};

  if (!values.doctorUserId.trim()) {
    errors.doctorUserId = "Doctor is required.";
  } else if (!UUID_PATTERN.test(values.doctorUserId.trim())) {
    errors.doctorUserId = "Doctor identifier must be a UUID.";
  }

  if (!values.facilityId.trim()) {
    errors.facilityId = "Facility is required.";
  } else if (!UUID_PATTERN.test(values.facilityId.trim())) {
    errors.facilityId = "Facility identifier must be a UUID.";
  }

  if (!values.appointmentDate) {
    errors.appointmentDate = "Appointment date is required.";
  } else if (values.appointmentDate < todayIsoDate()) {
    errors.appointmentDate = "Appointment date cannot be in the past.";
  }

  if (values.reason.length > REASON_MAX_LENGTH) {
    errors.reason = `Reason cannot exceed ${REASON_MAX_LENGTH} characters.`;
  }

  return errors;
}

function buildRequest(
  values: AppointmentBookFormValues,
): AppointmentBookingRequest {
  const trimmedReason = values.reason.trim();
  return {
    doctor_user_id: values.doctorUserId.trim(),
    facility_id: values.facilityId.trim(),
    appointment_date: values.appointmentDate,
    reason: trimmedReason.length > 0 ? trimmedReason : null,
  };
}

export function AppointmentBookForm({
  doctor,
  facilities,
  bookAction = bookAppointment,
  onBooked,
}: {
  doctor: BookingDoctor;
  facilities: readonly DoctorDiscoveryFacility[];
  bookAction?: (request: AppointmentBookingRequest) => Promise<AppointmentBookingResponse>;
  onBooked?: (response: AppointmentBookingResponse) => void;
}) {
  const choices = bookablePracticeFacilities(doctor, facilities);
  const facilityLabels = facilityOptionLabels(choices);
  const [values, setValues] = useState<AppointmentBookFormValues>(() => ({
    doctorUserId: doctor.id,
    facilityId: choices.find(facility => facility.id === doctor.facility_id)?.id ?? choices[0]?.id ?? "",
    appointmentDate: "",
    reason: "",
  }));
  const [errors, setErrors] = useState<
    Partial<Record<keyof AppointmentBookFormValues, string>>
  >({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const selectedPracticeDays = doctor.practice_days.filter(day => day.status === "ACTIVE" && day.facility_id === values.facilityId);
  const selectedWeekday = appointmentWeekday(values.appointmentDate);
  const selectedDateWindows = selectedPracticeDays.filter(day => day.weekday === selectedWeekday);
  const dailyCapacity = selectedDateWindows.length ? Math.max(...selectedDateWindows.map(day => day.max_patients)) : null;

  const updateField = useCallback(
    <K extends keyof AppointmentBookFormValues>(
      key: K,
      value: AppointmentBookFormValues[K],
    ) => {
      setValues((current) => ({ ...current, [key]: value }));
      setErrors((current) => {
        if (!current[key]) {
          return current;
        }
        const next = { ...current };
        delete next[key];
        return next;
      });
    },
    [],
  );

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (submitting) return;
    setSubmitError(null);

    const nextErrors = validateAppointmentBooking(values);
    if (!choices.some(facility => facility.id === values.facilityId)) {
      nextErrors.facilityId = "Choose a facility with available practice days.";
    }
    if (!nextErrors.appointmentDate) {
      if (!selectedDateWindows.length) {
        nextErrors.appointmentDate = "Choose a date matching the doctor’s available practice days at this facility.";
      }
    }
    if (Object.keys(nextErrors).length > 0) {
      setErrors(nextErrors);
      return;
    }

    setSubmitting(true);
    try {
      const response = await bookAction(buildRequest(values));
      onBooked?.(response);
    } catch (reason) {
      setSubmitError(
        citizenErrorMessage(
          reason,
          "We could not book this appointment right now. Please try again.",
        ),
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form
      aria-label="Book appointment"
      className="grid gap-4"
      data-testid="appointment-book-form"
      onSubmit={handleSubmit}
      noValidate
    >
      <div className="rounded-xl bg-teal-50 p-4 text-sm">
        <p className="font-bold text-slate-950">{doctor.name}</p>
        <p className="mt-1 text-slate-700">{facilityLabels.get(values.facilityId) ?? "Choose a practice facility below"}</p>
        <p className="mt-3 text-slate-600">Available practice days (Bangladesh time):</p>
        <ul className="mt-2 grid gap-1">
          {selectedPracticeDays.map(day => (
            <li key={day.id}>{day.weekday.charAt(0) + day.weekday.slice(1).toLowerCase()} · {day.start_time.slice(0, 5)}–{day.end_time.slice(0, 5)}</li>
          ))}
        </ul>
        {dailyCapacity !== null ? <p className="mt-3 text-slate-700">Published daily capacity: {dailyCapacity} patients. Remaining places are checked when you book.</p> : null}
        <p className="mt-3 text-slate-600">Your booking receives a queue serial, not a fixed appointment time. Availability is confirmed when you book.</p>
      </div>

      <label className="text-sm font-bold text-slate-700">
        Practice facility
        <select
          aria-invalid={errors.facilityId ? "true" : "false"}
          className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm"
          disabled={submitting || choices.length === 0}
          onChange={(event) => {
            setValues(current => ({ ...current, facilityId: event.target.value, appointmentDate: "" }));
            setErrors(current => ({ ...current, facilityId: undefined, appointmentDate: undefined }));
            setSubmitError(null);
          }}
          value={values.facilityId}
        >
          {choices.length === 0 ? <option value="">No practice facilities available</option> : null}
          {choices.map(facility => <option key={facility.id} value={facility.id}>{facilityLabels.get(facility.id) ?? facility.name}</option>)}
        </select>
      </label>
      {errors.facilityId ? <p className="-mt-2 text-sm text-rose-700" role="alert">{errors.facilityId}</p> : null}

      <label className="text-sm font-bold text-slate-700">
        Appointment date
        <input
          aria-invalid={errors.appointmentDate ? "true" : "false"}
          className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm"
          data-testid="appointment-date-input"
          disabled={submitting || choices.length === 0}
          min={todayIsoDate()}
          onChange={(event) => updateField("appointmentDate", event.target.value)}
          type="date"
          value={values.appointmentDate}
        />
      </label>
      {errors.appointmentDate ? (
        <p className="-mt-2 text-sm text-rose-700" data-testid="appointment-date-error">
          {errors.appointmentDate}
        </p>
      ) : null}

      <label className="text-sm font-bold text-slate-700">
        Reason for visit (optional)
        <textarea
          aria-invalid={errors.reason ? "true" : "false"}
          className="mt-2 min-h-24 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm"
          data-testid="reason-input"
          disabled={submitting || choices.length === 0}
          maxLength={REASON_MAX_LENGTH}
          onChange={(event) => updateField("reason", event.target.value)}
          placeholder="Briefly describe your symptoms or reason for the visit"
          value={values.reason}
        />
        <span className="mt-1 block text-xs text-slate-500">
          {values.reason.length}/{REASON_MAX_LENGTH} characters
        </span>
      </label>
      {errors.reason ? (
        <p className="-mt-2 text-sm text-rose-700" data-testid="reason-error">
          {errors.reason}
        </p>
      ) : null}

      {submitError ? (
        <p
          aria-live="polite"
          className="rounded-xl bg-rose-50 p-3 text-sm text-rose-800"
          data-testid="book-submit-error"
          role="alert"
        >
          {submitError}
        </p>
      ) : null}

      <div className="flex flex-wrap gap-3">
        <button
          className="min-h-11 rounded-xl bg-teal-700 px-5 text-sm font-bold text-white transition hover:bg-teal-800 disabled:cursor-wait disabled:opacity-60"
          data-testid="book-submit"
          disabled={submitting || choices.length === 0}
          type="submit"
        >
          {submitting ? "Booking…" : "Book appointment"}
        </button>
      </div>
    </form>
  );
}
