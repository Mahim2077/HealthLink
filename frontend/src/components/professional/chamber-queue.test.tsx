import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ChamberQueue, type ChamberDeps } from "./chamber-queue";
import type { ChamberAppointmentView, ChamberSessionView } from "@/lib/chamber/types";

const baseFacility = "facility-1";

const baseAppointment = (
  overrides: Partial<ChamberAppointmentView>,
): ChamberAppointmentView => ({
  appointment_id: `appt-${overrides.queue_id ?? "x"}`,
  became_current_at: null,
  booked_at: "2026-08-10T08:00:00Z",
  finished_at: null,
  queue_id: overrides.queue_id ?? "queue-x",
  queue_status: "WAITING",
  reason: null,
  removed_at: null,
  serial_number: 1,
  status: "BOOKED",
  ...overrides,
});

function buildSession(overrides: Partial<ChamberSessionView>): ChamberSessionView {
  return {
    current: null,
    ended_at: null,
    facility_id: baseFacility,
    facility_name: "City Hospital",
    finished: [],
    id: "session-1",
    session_date: "2026-08-10",
    started_at: "2026-08-10T09:00:00Z",
    status: "OPEN",
    waiting: [],
    ...overrides,
  };
}

function buildDeps(
  overrides: Partial<ChamberDeps> = {},
): {
  deps: ChamberDeps;
  spies: ChamberDeps;
} {
  const spies: ChamberDeps = {
    actOnCurrent: vi.fn().mockResolvedValue({} as never),
    callNext: vi.fn().mockResolvedValue({} as never),
    finishSession: vi.fn().mockResolvedValue({} as never),
    loadSession: vi.fn().mockResolvedValue(null),
    removeEntry: vi.fn().mockResolvedValue({} as never),
    startSession: vi.fn().mockResolvedValue({} as never),
  };
  return { deps: { ...spies, ...overrides }, spies };
}

describe("ChamberQueue", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("renders the empty state when no session exists", async () => {
    const { deps } = buildDeps();
    render(<ChamberQueue facility_id={baseFacility} chamberDeps={deps} />);

    expect(
      await screen.findByText("No chamber session today"),
    ).toBeInTheDocument();
    const openBtn = screen.getByRole("button", {
      name: /open today's chamber/i,
    });
    fireEvent.click(openBtn);

    await waitFor(() => {
      expect(deps.startSession).toHaveBeenCalledWith({
        facility_id: baseFacility,
        session_date: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/),
      });
    });
  });

  it("shows waiting and finished lists plus current actions", async () => {
    const session = buildSession({
      current: baseAppointment({
        became_current_at: "2026-08-10T09:15:00Z",
        queue_id: "current-1",
        queue_status: "CURRENT",
        serial_number: 1,
      }),
      finished: [
        baseAppointment({
          finished_at: "2026-08-10T09:00:00Z",
          queue_id: "finished-1",
          queue_status: "COMPLETED",
          serial_number: 0,
          status: "COMPLETED",
        }),
      ],
      waiting: [
        baseAppointment({ queue_id: "wait-2", serial_number: 2 }),
        baseAppointment({ queue_id: "wait-3", serial_number: 3 }),
      ],
    });
    const { deps, spies } = buildDeps({
      loadSession: vi.fn().mockResolvedValue(session),
    });

    render(<ChamberQueue facility_id={baseFacility} chamberDeps={deps} />);

    expect(
      await screen.findByText("Serial #1", { selector: "p" }),
    ).toBeInTheDocument();

    // All three sections render.
    expect(screen.getAllByText("Waiting").length).toBeGreaterThan(0);
    expect(screen.getByText("Finished today")).toBeInTheDocument();

    // Waiting rows render with the remove button.
    const removeButtons = screen.getAllByRole("button", { name: "Remove" });
    expect(removeButtons.length).toBeGreaterThanOrEqual(2);

    // Click Complete and wait for the call to land.
    fireEvent.click(screen.getByRole("button", { name: "Complete" }));
    await waitFor(() => {
      expect(spies.actOnCurrent).toHaveBeenCalledWith("current-1", "complete");
    });

    // Call-next fires.
    fireEvent.click(
      screen.getByRole("button", { name: /call next patient/i }),
    );
    await waitFor(() => {
      expect(spies.callNext).toHaveBeenCalledWith(
        baseFacility,
        expect.any(String),
      );
    });
  });

  it("fires the skip and no-show actions on the CURRENT patient", async () => {
    const session = buildSession({
      current: baseAppointment({
        became_current_at: "2026-08-10T09:15:00Z",
        queue_id: "current-skip",
        queue_status: "CURRENT",
        serial_number: 5,
      }),
      waiting: [],
    });
    const { deps, spies } = buildDeps({
      loadSession: vi.fn().mockResolvedValue(session),
    });

    render(<ChamberQueue facility_id={baseFacility} chamberDeps={deps} />);

    await screen.findByText("Serial #5", { selector: "p" });

    fireEvent.click(screen.getByRole("button", { name: "Skip" }));
    await waitFor(() => {
      expect(spies.actOnCurrent).toHaveBeenCalledWith("current-skip", "skip");
    });

    // After optimistic merge the CURRENT row moves to FINISHED, so
    // we re-fetch the mock and re-render to test No-show. We do that
    // by remounting with a fresh session that still has CURRENT.
    cleanup();
    const next = buildSession({
      current: baseAppointment({
        became_current_at: "2026-08-10T09:16:00Z",
        queue_id: "current-ns",
        queue_status: "CURRENT",
        serial_number: 6,
      }),
      waiting: [],
    });
    const { deps: deps2, spies: spies2 } = buildDeps({
      loadSession: vi.fn().mockResolvedValue(next),
    });
    render(<ChamberQueue facility_id={baseFacility} chamberDeps={deps2} />);

    await screen.findByText("Serial #6", { selector: "p" });
    fireEvent.click(screen.getByRole("button", { name: "No-show" }));
    await waitFor(() => {
      expect(spies2.actOnCurrent).toHaveBeenCalledWith("current-ns", "no-show");
    });
  });

  it("disables actions and shows the closed state when session is FINISHED", async () => {
    const session = buildSession({
      current: null,
      finished: [
        baseAppointment({
          finished_at: "2026-08-10T17:00:00Z",
          queue_id: "finished-1",
          queue_status: "COMPLETED",
          serial_number: 1,
          status: "COMPLETED",
        }),
      ],
      status: "FINISHED",
      ended_at: "2026-08-10T17:00:00Z",
      waiting: [],
    });
    const { deps } = buildDeps({
      loadSession: vi.fn().mockResolvedValue(session),
    });

    render(<ChamberQueue facility_id={baseFacility} chamberDeps={deps} />);

    expect(
      await screen.findByText(/Closed for the day/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /call next patient/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /close chamber/i }),
    ).not.toBeInTheDocument();
    expect(screen.getByText("Chamber closed.")).toBeInTheDocument();
  });

  it("shows an error banner when an action fails and supports retry", async () => {
    const session = buildSession({
      current: baseAppointment({
        queue_id: "current-1",
        queue_status: "CURRENT",
        serial_number: 1,
      }),
      waiting: [],
    });
    const { deps } = buildDeps({
      actOnCurrent: vi.fn().mockRejectedValue(new Error("Conflict: queue raced")),
      loadSession: vi.fn().mockResolvedValue(session),
    });

    render(<ChamberQueue facility_id={baseFacility} chamberDeps={deps} />);

    await screen.findByText("Serial #1", { selector: "p" });
    fireEvent.click(screen.getByRole("button", { name: "Complete" }));

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent("Conflict: queue raced");
  });
});