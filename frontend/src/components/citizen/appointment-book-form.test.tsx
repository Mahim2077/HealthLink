import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/errors";
import type { AppointmentBookingResponse } from "@/lib/appointments/types";

import {
  AppointmentBookForm,
  validateAppointmentBooking,
} from "./appointment-book-form";

const bookingResponse: AppointmentBookingResponse = {
  id: "appointment-1",
  citizen_id: "citizen-1",
  doctor_role_registration_id: "registration-1",
  doctor_user_id: "11111111-1111-1111-1111-111111111111",
  facility_id: "22222222-2222-2222-2222-222222222222",
  facility_name: "Square Hospital",
  appointment_date: "2099-01-15",
  serial_number: 1,
  status: "BOOKED",
  reason: "Annual checkup",
  booked_at: "2099-01-10T08:00:00Z",
  queue: {
    id: "queue-1",
    queue_status: "WAITING",
    became_current_at: null,
    finished_at: null,
    removed_at: null,
  },
};

const doctor = {
  id: bookingResponse.doctor_user_id,
  name: "Dr Test",
  facility_id: bookingResponse.facility_id,
  facility_name: bookingResponse.facility_name,
  practice_days: [{ id: "schedule-1", facility_id: bookingResponse.facility_id, facility_name: bookingResponse.facility_name, weekday: "THURSDAY" as const, start_time: "09:00:00", end_time: "12:00:00", max_patients: 20, status: "ACTIVE" as const }],
};

function fillForm(): void {
  fireEvent.change(screen.getByTestId("appointment-date-input"), {
    target: { value: "2099-01-15" },
  });
  fireEvent.change(screen.getByTestId("reason-input"), {
    target: { value: "Annual checkup" },
  });
}

describe("AppointmentBookForm", () => {
  it("submits a trimmed booking request and notifies onBooked", async () => {
    const onBooked = vi.fn();
    const bookAction = vi.fn().mockResolvedValue(bookingResponse);

    render(
      <AppointmentBookForm doctor={doctor}
        bookAction={bookAction}
        onBooked={onBooked}
      />,
    );
    fillForm();
    fireEvent.click(screen.getByTestId("book-submit"));

    await waitFor(() => expect(bookAction).toHaveBeenCalledOnce());
    expect(bookAction).toHaveBeenCalledWith({
      doctor_user_id: "11111111-1111-1111-1111-111111111111",
      facility_id: "22222222-2222-2222-2222-222222222222",
      appointment_date: "2099-01-15",
      reason: "Annual checkup",
    });
    expect(onBooked).toHaveBeenCalledWith(bookingResponse);
  });

  it("coerces a whitespace-only reason into a null payload value", async () => {
    const bookAction = vi.fn().mockResolvedValue(bookingResponse);

    render(<AppointmentBookForm doctor={doctor} bookAction={bookAction} />);
    fillForm();
    fireEvent.change(screen.getByTestId("reason-input"), {
      target: { value: "   " },
    });
    fireEvent.click(screen.getByTestId("book-submit"));

    await waitFor(() => expect(bookAction).toHaveBeenCalledOnce());
    expect(bookAction.mock.calls[0][0].reason).toBeNull();
  });

  it("surfaces client-side validation without calling the action", () => {
    const bookAction = vi.fn();
    render(<AppointmentBookForm doctor={doctor} bookAction={bookAction} />);

    fireEvent.click(screen.getByTestId("book-submit"));

    expect(screen.queryByTestId("doctor-user-id-input")).not.toBeInTheDocument();
    expect(screen.queryByTestId("facility-id-input")).not.toBeInTheDocument();
    expect(
      screen.getByTestId("appointment-date-error"),
    ).toHaveTextContent("Appointment date is required.");
    expect(bookAction).not.toHaveBeenCalled();
  });

  it("rejects past dates before submitting", () => {
    const bookAction = vi.fn();
    render(<AppointmentBookForm doctor={doctor} bookAction={bookAction} />);

    fireEvent.change(screen.getByTestId("appointment-date-input"), {
      target: { value: "2000-01-01" },
    });
    fireEvent.click(screen.getByTestId("book-submit"));

    expect(
      screen.getByTestId("appointment-date-error"),
    ).toHaveTextContent(/cannot be in the past/);
    expect(bookAction).not.toHaveBeenCalled();
  });

  it("renders the API error message returned by the booking endpoint", async () => {
    const bookAction = vi
      .fn()
      .mockRejectedValue(new ApiError(409, "Doctor is not available on that date."));

    render(<AppointmentBookForm doctor={doctor} bookAction={bookAction} />);
    fillForm();
    fireEvent.click(screen.getByTestId("book-submit"));

    expect(
      await screen.findByTestId("book-submit-error"),
    ).toHaveTextContent("Doctor is not available on that date.");
  });
});

describe("validateAppointmentBooking", () => {
  const valid = {
    doctorUserId: "11111111-1111-1111-1111-111111111111",
    facilityId: "22222222-2222-2222-2222-222222222222",
    appointmentDate: "2099-01-15",
    reason: "",
  };

  it("returns no errors for a valid payload", () => {
    expect(validateAppointmentBooking(valid)).toEqual({});
  });

  it("flags every missing required field", () => {
    expect(
      validateAppointmentBooking({ ...valid, doctorUserId: "" }).doctorUserId,
    ).toBe("Doctor is required.");
    expect(
      validateAppointmentBooking({ ...valid, facilityId: "" }).facilityId,
    ).toBe("Facility is required.");
    expect(
      validateAppointmentBooking({ ...valid, appointmentDate: "" })
        .appointmentDate,
    ).toBe("Appointment date is required.");
  });

  it("enforces the documented reason length", () => {
    const tooLong = "x".repeat(2001);
    expect(
      validateAppointmentBooking({ ...valid, reason: tooLong }).reason,
    ).toMatch(/cannot exceed 2000 characters/);
  });
});
