import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "@/components/auth/auth-provider";
import { accessTokenStore } from "@/lib/auth/token-store";
import type { AppointmentListResponse } from "@/lib/appointments/types";
import type { Portal } from "@/lib/auth/types";

import { AppointmentsView } from "./page";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
}));

const appointmentHistory: AppointmentListResponse = {
  appointments: [
    {
      id: "11111111-1111-1111-1111-111111111111",
      doctor_user_id: "22222222-2222-2222-2222-222222222222",
      doctor_name: "Dr. Amina Rahman",
      facility_id: "33333333-3333-3333-3333-333333333333",
      facility_name: "HealthLink Clinic",
      appointment_date: "2099-01-05",
      serial_number: 4,
      status: "BOOKED",
      booked_at: "2026-09-10T08:00:00Z",
      cancelled_at: null,
      completed_at: null,
      prescription_id: null,
    },
  ],
};

function createToken(portal: Portal): string {
  const issuedAt = Math.floor(Date.now() / 1000);
  const encode = (value: Record<string, unknown>) =>
    btoa(JSON.stringify(value))
      .replace(/=/g, "")
      .replace(/\+/g, "-")
      .replace(/\//g, "_");

  return (
    encode({ alg: "none", typ: "JWT" }) +
    "." +
    encode({
      exp: issuedAt + 1800,
      iat: issuedAt,
      jti: "token-1",
      portal,
      sid: "session-1",
      sub: "citizen-1",
      type: "access",
    }) +
    ".x"
  );
}

describe("AppointmentsView", () => {
  beforeEach(() => {
    accessTokenStore.clear();
    act(() => accessTokenStore.set(createToken("CITIZEN")));
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("cancels a booked appointment and updates its history status", async () => {
    const loadAction = vi.fn().mockResolvedValue(appointmentHistory);
    const cancelAction = vi.fn().mockResolvedValue({
      appointment_id: appointmentHistory.appointments[0].id,
      status: "CANCELLED",
      cancelled_at: "2026-09-10T09:00:00Z",
      queue_id: "44444444-4444-4444-4444-444444444444",
      queue_status: "CANCELLED",
      removed_at: "2026-09-10T09:00:00Z",
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(
      <AuthProvider>
        <AppointmentsView
          cancelAction={cancelAction}
          loadAction={loadAction}
        />
      </AuthProvider>,
    );

    fireEvent.click(
      await screen.findByRole("button", { name: "Cancel appointment" }),
    );

    expect(window.confirm).toHaveBeenCalledOnce();
    expect(cancelAction).toHaveBeenCalledWith(
      appointmentHistory.appointments[0].id,
    );
    expect(
      await screen.findByText(/Appointment cancelled\. Its serial remains/),
    ).toBeInTheDocument();
    expect(screen.getByTestId("appointment-status")).toHaveTextContent(
      "Cancelled",
    );
    expect(
      screen.queryByRole("button", { name: "Cancel appointment" }),
    ).not.toBeInTheDocument();
  });
});
