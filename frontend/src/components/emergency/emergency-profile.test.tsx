import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { EmergencyProfileContext, EmergencyProfileEditor, EmergencyProfilePage } from "./emergency-profile";
import type { EmergencyProfile } from "@/lib/emergency/api";

const mocks = vi.hoisted(() => ({ save: vi.fn(), load: vi.fn(), current: vi.fn(), auth: vi.fn() }));
vi.mock("@/lib/emergency/api", () => ({ saveEmergencyProfile: mocks.save, loadEmergencyProfile: mocks.load, loadCurrentEmergencyProfile: mocks.current }));
vi.mock("@/components/auth/auth-provider", () => ({ usePortalAuth: mocks.auth }));
const initial: EmergencyProfile = { citizen_id: "one", blood_group: "O+", updated_at: null, allergies: null, chronic_conditions: null, current_medications: null, emergency_contact_name: null, emergency_contact_phone: null, special_notes: null };

describe("Emergency medical profiles", () => {
  beforeEach(() => vi.clearAllMocks());
  it("retains failed edits and sends only editable fields", async () => {
    mocks.save.mockRejectedValue(new Error("offline"));
    render(<EmergencyProfileEditor initial={initial} />);
    fireEvent.change(screen.getByLabelText("Allergies"), { target: { value: "Latex" } });
    fireEvent.click(screen.getByRole("button", { name: "Save emergency profile" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Your changes are still here");
    expect(screen.getByLabelText("Allergies")).toHaveValue("Latex");
    expect(mocks.save.mock.calls[0][0]).toEqual({ allergies: "Latex", chronic_conditions: null, current_medications: null, emergency_contact_name: null, emergency_contact_phone: null, special_notes: null });
  });
  it("blocks duplicate saves and edits while a request is pending", async () => {
    let resolve!: (value: EmergencyProfile) => void;
    mocks.save.mockReturnValue(new Promise<EmergencyProfile>(done => { resolve = done; }));
    render(<EmergencyProfileEditor initial={initial} />);
    fireEvent.click(screen.getByRole("button", { name: "Save emergency profile" }));
    expect(screen.getByLabelText("Allergies")).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Saving…" }));
    expect(mocks.save).toHaveBeenCalledTimes(1);
    await act(async () => resolve(initial));
    expect(screen.getByRole("status")).toHaveTextContent("Emergency profile saved");
  });
  it("never loads citizen data in the wrong portal", () => {
    mocks.auth.mockReturnValue({ status: "authenticated", isRequiredPortal: false, refreshSession: vi.fn() });
    render(<EmergencyProfilePage />);
    expect(screen.getByText("Portal access required")).toBeInTheDocument();
    expect(mocks.load).not.toHaveBeenCalled();
  });
  it("discards the previous patient's result after a context switch", async () => {
    let finishOld!: (value: EmergencyProfile) => void;
    mocks.current.mockImplementation((id: string) => id === "one" ? new Promise<EmergencyProfile>(resolve => { finishOld = resolve; }) : Promise.resolve({ ...initial, citizen_id: "two", allergies: "Current allergy" }));
    const view = render(<EmergencyProfileContext citizenId="one" />);
    view.rerender(<EmergencyProfileContext citizenId="two" />);
    expect(await screen.findByText("Current allergy")).toBeInTheDocument();
    await act(async () => finishOld({ ...initial, allergies: "Previous allergy" }));
    expect(screen.queryByText("Previous allergy")).toBeNull();
    expect(mocks.current).toHaveBeenCalledWith("two");
  });
});
