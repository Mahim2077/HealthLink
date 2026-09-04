import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    get: apiMocks.get,
    post: apiMocks.post,
  },
}));

import {
  bookAppointment,
  finishAppointment,
  listMyAppointments,
} from "./api";

describe("Appointments API", () => {
  beforeEach(() => {
    apiMocks.get.mockReset();
    apiMocks.post.mockReset();
  });

  it("books an appointment through POST citizens/appointments", async () => {
    const request = {
      doctor_user_id: "11111111-1111-1111-1111-111111111111",
      facility_id: "22222222-2222-2222-2222-222222222222",
      appointment_date: "2026-08-15",
      reason: "Annual checkup",
    };
    const response = {
      id: "appointment-1",
      citizen_id: "citizen-1",
      doctor_role_registration_id: "registration-1",
      doctor_user_id: request.doctor_user_id,
      facility_id: request.facility_id,
      facility_name: "Square Hospital",
      appointment_date: request.appointment_date,
      serial_number: 1,
      status: "BOOKED",
      reason: request.reason,
      booked_at: "2026-08-10T08:00:00Z",
      queue: {
        id: "queue-1",
        queue_status: "WAITING",
        became_current_at: null,
        finished_at: null,
        removed_at: null,
      },
    };
    apiMocks.post.mockResolvedValue(response);

    await expect(bookAppointment(request)).resolves.toEqual(response);
    expect(apiMocks.post).toHaveBeenCalledWith(
      "citizens/appointments",
      request,
    );
  });

  it("allows omitting the reason field when booking", async () => {
    const request = {
      doctor_user_id: "11111111-1111-1111-1111-111111111111",
      facility_id: "22222222-2222-2222-2222-222222222222",
      appointment_date: "2026-08-15",
      reason: null,
    };
    apiMocks.post.mockResolvedValue({ id: "appointment-1", serial_number: 1 });

    await bookAppointment(request);
    expect(apiMocks.post).toHaveBeenCalledWith(
      "citizens/appointments",
      request,
    );
  });

  it("lists the citizen's appointments through GET citizens/appointments", async () => {
    const response = {
      appointments: [
        {
          id: "appointment-1",
          doctor_user_id: "11111111-1111-1111-1111-111111111111",
          doctor_name: "Dr. Amina Rahman",
          facility_id: "22222222-2222-2222-2222-222222222222",
          facility_name: "Square Hospital",
          appointment_date: "2026-08-15",
          serial_number: 1,
          status: "BOOKED",
          booked_at: "2026-08-10T08:00:00Z",
          cancelled_at: null,
          completed_at: null,
        },
      ],
    };
    apiMocks.get.mockResolvedValue(response);

    await expect(listMyAppointments()).resolves.toEqual(response);
    expect(apiMocks.get).toHaveBeenCalledWith("citizens/appointments");
  });

  it("finishes the current appointment through the canonical Phase 14 route", async () => {
    apiMocks.post.mockResolvedValue({
      appointment_id: "appointment-1",
      appointment_status: "COMPLETED",
      queue_status: "DONE",
      visit_status: "FINALIZED",
    });

    await finishAppointment("appointment-1");

    expect(apiMocks.post).toHaveBeenCalledWith(
      "appointments/appointment-1/finish",
      {},
    );
  });

  it("propagates errors thrown by the api client", async () => {
    const failure = new Error("Network unavailable");
    apiMocks.get.mockRejectedValue(failure);

    await expect(listMyAppointments()).rejects.toBe(failure);
  });
});
