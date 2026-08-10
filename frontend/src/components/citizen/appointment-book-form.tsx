"use client";

import { useCallback, useState, type FormEvent } from "react";

import { citizenErrorMessage } from "@/lib/citizen/presentation";
import { bookAppointment } from "@/lib/appointments/api";
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

function todayIsoDate(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
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
  initialDoctorUserId = "",
  initialFacilityId = "",
  bookAction = bookAppointment,
  onBooked,
}: {
  initialDoctorUserId?: string;
  initialFacilityId?: string;
  bookAction?: (request: AppointmentBookingRequest) => Promise<AppointmentBookingResponse>;
  onBooked?: (response: AppointmentBookingResponse) => void;
}) {
  const [values, setValues] = useState<AppointmentBookFormValues>({
    doctorUserId: initialDoctorUserId,
    facilityId: initialFacilityId,
    appointmentDate: "",
    reason: "",
  });
  const [errors, setErrors] = useState<
    Partial<Record<keyof AppointmentBookFormValues, string>>
  >({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

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
    setSubmitError(null);

    const nextErrors = validateAppointmentBooking(values);
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
      <label className="text-sm font-bold text-slate-700">
        Doctor identifier (UUID)
        <input
          aria-invalid={errors.doctorUserId ? "true" : "false"}
          className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm"
          data-testid="doctor-user-id-input"
          disabled={submitting}
          onChange={(event) => updateField("doctorUserId", event.target.value)}
          placeholder="00000000-0000-0000-0000-000000000000"
          value={values.doctorUserId}
        />
      </label>
      {errors.doctorUserId ? (
        <p className="-mt-2 text-sm text-rose-700" data-testid="doctor-user-id-error">
          {errors.doctorUserId}
        </p>
      ) : null}

      <label className="text-sm font-bold text-slate-700">
        Facility identifier (UUID)
        <input
          aria-invalid={errors.facilityId ? "true" : "false"}
          className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm"
          data-testid="facility-id-input"
          disabled={submitting}
          onChange={(event) => updateField("facilityId", event.target.value)}
          placeholder="00000000-0000-0000-0000-000000000000"
          value={values.facilityId}
        />
      </label>
      {errors.facilityId ? (
        <p className="-mt-2 text-sm text-rose-700" data-testid="facility-id-error">
          {errors.facilityId}
        </p>
      ) : null}

      <label className="text-sm font-bold text-slate-700">
        Appointment date
        <input
          aria-invalid={errors.appointmentDate ? "true" : "false"}
          className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm"
          data-testid="appointment-date-input"
          disabled={submitting}
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
          disabled={submitting}
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
          disabled={submitting}
          type="submit"
        >
          {submitting ? "Booking…" : "Book appointment"}
        </button>
      </div>
    </form>
  );
}