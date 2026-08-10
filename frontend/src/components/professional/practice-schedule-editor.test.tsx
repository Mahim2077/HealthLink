import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PracticeScheduleEditor } from "./practice-schedule-editor";
import type { ScheduleEditorDeps } from "./practice-schedule-editor";

const baseEntry = {
  created_at: "2026-08-10T00:00:00Z",
  end_time: "12:00:00",
  facility_id: "facility-1",
  facility_name: "Home Hospital",
  id: "schedule-1",
  max_patients: 20,
  start_time: "09:00:00",
  status: "ACTIVE" as const,
  updated_at: "2026-08-10T00:00:00Z",
  weekday: "MONDAY" as const,
};

const baseFacility = {
  facility_type: "HOSPITAL",
  id: "facility-1",
  is_active: true,
  is_verified_assignment: true,
  name: "Home Hospital",
};

function buildDeps(
  overrides: Partial<ScheduleEditorDeps> = {},
): { deps: Partial<ScheduleEditorDeps>; spies: ScheduleEditorDeps } {
  const spies: ScheduleEditorDeps = {
    createRow: vi.fn().mockResolvedValue({ schedule: baseEntry }),
    deleteRow: vi.fn().mockResolvedValue({ id: baseEntry.id, deleted_at: "2026-08-11T00:00:00Z" }),
    loadFacilities: vi.fn().mockResolvedValue([baseFacility]),
    loadSchedule: vi.fn().mockResolvedValue([baseEntry]),
    updateRow: vi.fn().mockResolvedValue(baseEntry),
  };
  return { deps: { ...spies, ...overrides }, spies };
}

describe("PracticeScheduleEditor", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders an empty state when no schedule rows exist", async () => {
    const { deps } = buildDeps({ loadSchedule: vi.fn().mockResolvedValue([]) });
    render(<PracticeScheduleEditor deps={deps} />);

    expect(await screen.findByText("No practice windows yet")).toBeInTheDocument();
    expect(
      screen.getByText("Add the first weekly window to start publishing availability."),
    ).toBeInTheDocument();
  });

  it("renders an error state when the load fails", async () => {
    const { deps } = buildDeps({
      loadSchedule: vi.fn().mockRejectedValue(new Error("Server down")),
    });
    render(<PracticeScheduleEditor deps={deps} />);

    expect(
      await screen.findByText("Practice schedule unavailable"),
    ).toBeInTheDocument();
    expect(screen.getByText("Server down")).toBeInTheDocument();
  });

  it("lists existing schedule rows", async () => {
    const { deps } = buildDeps();
    render(<PracticeScheduleEditor deps={deps} />);

    expect(await screen.findByText("Home Hospital")).toBeInTheDocument();
    expect(screen.getByText(/09:00:00.*12:00:00/)).toBeInTheDocument();
    expect(screen.getByText(/capacity 20/)).toBeInTheDocument();
  });

  it("calls createRow when the form is submitted with valid input", async () => {
    const { deps, spies } = buildDeps({
      loadSchedule: vi
        .fn()
        .mockResolvedValueOnce([])
        .mockResolvedValue([baseEntry]),
    });
    render(<PracticeScheduleEditor deps={deps} />);

    await screen.findByText("No practice windows yet");

    fireEvent.change(screen.getByLabelText(/Facility/i), {
      target: { value: "facility-1" },
    });
    fireEvent.change(screen.getByLabelText(/Start time/i), {
      target: { value: "10:00" },
    });
    fireEvent.change(screen.getByLabelText(/End time/i), {
      target: { value: "11:00" },
    });
    fireEvent.change(screen.getByLabelText(/Max patients/i), {
      target: { value: "15" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Publish window/i }));

    await waitFor(() => {
      expect(spies.createRow).toHaveBeenCalledWith({
        end_time: "11:00",
        facility_id: "facility-1",
        max_patients: 15,
        start_time: "10:00",
        status: "ACTIVE",
        weekday: "MONDAY",
      });
    });
  });

  it("rejects end time <= start time with a validation message", async () => {
    const { deps, spies } = buildDeps();
    render(<PracticeScheduleEditor deps={deps} />);

    await screen.findByText("Home Hospital");

    fireEvent.change(screen.getByLabelText(/Start time/i), {
      target: { value: "12:00" },
    });
    fireEvent.change(screen.getByLabelText(/End time/i), {
      target: { value: "11:00" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Publish window/i }));

    expect(
      await screen.findByText("End time must be after start time."),
    ).toBeInTheDocument();
    expect(spies.createRow).not.toHaveBeenCalled();
  });

  it("calls deleteRow when the Remove button is clicked", async () => {
    const { deps, spies } = buildDeps();
    render(<PracticeScheduleEditor deps={deps} />);

    const removeButton = await screen.findByRole("button", { name: /^Remove$/ });
    fireEvent.click(removeButton);

    await waitFor(() => {
      expect(spies.deleteRow).toHaveBeenCalledWith("schedule-1");
    });
  });

  it("loads both schedule and facilities on mount", async () => {
    const { deps, spies } = buildDeps();
    render(<PracticeScheduleEditor deps={deps} />);

    await waitFor(() => {
      expect(spies.loadSchedule).toHaveBeenCalledTimes(1);
      expect(spies.loadFacilities).toHaveBeenCalledTimes(1);
    });
  });
});