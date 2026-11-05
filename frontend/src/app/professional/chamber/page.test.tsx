import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ me: vi.fn(), facilities: vi.fn(), load: vi.fn(), start: vi.fn() }));
vi.mock("@/components/auth/auth-provider", () => ({ usePortalAuth: () => ({
  status: "authenticated", isRequiredPortal: true, refreshSession: vi.fn(),
}) }));
vi.mock("@/lib/professional/api", () => ({ loadProfessionalMe: mocks.me }));
vi.mock("@/lib/chamber/api", () => ({
  loadChamberFacilities: mocks.facilities, loadChamberSession: mocks.load,
  startChamberSession: mocks.start, actOnCurrentPatient: vi.fn(), callNextPatient: vi.fn(),
  finishChamberSession: vi.fn(), removeQueueEntry: vi.fn(),
}));

import ChamberPage from "./page";

describe("Doctor chamber facility selection", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mocks.me.mockResolvedValue({ role_code: "DOCTOR", role_name: "Doctor", verification_status: "VERIFIED",
      facility: { id: "primary", name: "Primary Hospital" } });
    mocks.facilities.mockResolvedValue([{ id: "primary", name: "Primary Hospital" },
      { id: "secondary", name: "Secondary Hospital" }]);
    mocks.load.mockResolvedValue(null);
  });
  afterEach(cleanup);

  it("opens the selected secondary facility with a fresh queue context", async () => {
    render(<ChamberPage />);
    const selector = await screen.findByRole("combobox", { name: "Chamber facility" });
    await screen.findByText("No chamber session today");
    expect(selector).toHaveValue("primary");
    fireEvent.change(selector, { target: { value: "secondary" } });
    await waitFor(() => expect(mocks.load).toHaveBeenLastCalledWith("secondary", expect.any(String)));
    fireEvent.click(await screen.findByRole("button", { name: /open today's chamber/i }));
    await waitFor(() => expect(mocks.start).toHaveBeenCalledWith({ facility_id: "secondary", session_date: expect.any(String) }));
  });

  it("does not render an old facility's delayed queue after switching", async () => {
    let finishPrimary!: (value: unknown) => void;
    mocks.load.mockImplementationOnce(() => new Promise(resolve => { finishPrimary = resolve; }))
      .mockResolvedValue(null);
    render(<ChamberPage />);
    const selector = await screen.findByRole("combobox", { name: "Chamber facility" });
    await waitFor(() => expect(mocks.load).toHaveBeenCalledTimes(1));
    fireEvent.change(selector, { target: { value: "secondary" } });
    await screen.findByText("No chamber session today");
    await act(async () => finishPrimary({ id: "old", facility_id: "primary", facility_name: "Primary Hospital",
      status: "ACTIVE", current: null, waiting: [{ serial_number: 99, queue_id: "old-patient" }], finished: [] }));
    expect(screen.queryByText(/#99/)).not.toBeInTheDocument();
    expect(selector).toHaveValue("secondary");
    expect(screen.getByText("No chamber session today")).toBeVisible();
  });

  it("retries a facility-list failure without silently showing the wrong queue", async () => {
    mocks.facilities.mockRejectedValueOnce(new Error("Facility list unavailable"));
    render(<ChamberPage />);
    await screen.findByRole("heading", { name: "Chamber unavailable" });
    expect(mocks.load).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: /try again/i }));
    await screen.findByRole("combobox", { name: "Chamber facility" });
    await screen.findByText("No chamber session today");
    expect(mocks.facilities).toHaveBeenCalledTimes(2);
  });
});
