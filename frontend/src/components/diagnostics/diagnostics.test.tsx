import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DiagnosticRequestPanel } from "./diagnostic-request-panel";
import { DiagnosticList } from "./diagnostic-list";
import { DiagnosticsPage } from "./diagnostics-page";

const mocks = vi.hoisted(() => ({ create: vi.fn(), search: vi.fn(), assign: vi.fn(), citizen: vi.fn(), professional: vi.fn(), me: vi.fn(), auth: vi.fn() }));
vi.mock("@/lib/diagnostics/api", () => ({ createDiagnosticTest: mocks.create, listDiagnosticTechnicians: mocks.search, assignDiagnosticTest: mocks.assign, listCitizenDiagnostics: mocks.citizen, listProfessionalDiagnostics: mocks.professional, transitionDiagnosticTest: vi.fn() }));
vi.mock("@/lib/professional/api", () => ({ loadProfessionalMe: mocks.me }));
vi.mock("@/components/auth/auth-provider", () => ({ usePortalAuth: mocks.auth }));

const testRecord = {
  id: "test-1", citizen_id: "citizen-1", visit_id: "visit-1", requested_by_role_registration_id: "doctor-1", assigned_to_role_registration_id: null,
  facility_id: "facility-1", facility_name: "City Hospital", test_name: "CBC", instructions: null, status: "REQUESTED" as const,
  requested_by_name: "Doctor", assigned_to_name: null, created_at: "2026-09-12", updated_at: "2026-09-12",
};

describe("Diagnostic safety and assignment", () => {
  beforeEach(() => { vi.clearAllMocks(); mocks.search.mockResolvedValue([]); });

  it("keeps failed requests and binds submission to the displayed visit", async () => {
    mocks.create.mockRejectedValue(new Error("Consultation changed"));
    const onEditStateChange = vi.fn();
    render(<DiagnosticRequestPanel visitId="visit-1" onEditStateChange={onEditStateChange} />);
    fireEvent.change(screen.getByLabelText("Test name"), { target: { value: "CBC" } });
    fireEvent.click(screen.getByRole("button", { name: "Request test" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Consultation changed");
    expect(mocks.create).toHaveBeenCalledWith(expect.objectContaining({ visit_id: "visit-1", test_name: "CBC" }));
    expect(screen.getByLabelText("Test name")).toHaveValue("CBC");
    expect(onEditStateChange).toHaveBeenLastCalledWith({ dirty: true, saving: false });
  });

  it("disables edits and duplicate submission during a request", async () => {
    let resolve!: (value: unknown) => void;
    mocks.create.mockReturnValue(new Promise(r => { resolve = r; }));
    render(<DiagnosticRequestPanel visitId="visit-1" onEditStateChange={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Test name"), { target: { value: "CBC" } });
    fireEvent.click(screen.getByRole("button", { name: "Request test" }));
    expect(screen.getByLabelText("Test name")).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Requesting…" }));
    expect(mocks.create).toHaveBeenCalledTimes(1);
    await act(async () => resolve({}));
    expect(screen.getByLabelText("Test name")).toHaveValue("");
  });

  it("searches and assigns a technician using the selected test's facility", async () => {
    mocks.search.mockResolvedValue([{ role_registration_id: "lab-1", full_name: "Amina", designation: "Technician", facility_id: "facility-1", facility_name: "City Hospital" }]);
    mocks.assign.mockResolvedValue({ ...testRecord, assigned_to_role_registration_id: "lab-1", assigned_to_name: "Amina" });
    render(<DiagnosticList loadAction={async () => ({ tests: [testRecord] })} role="doctor" />);
    fireEvent.click(await screen.findByRole("button", { name: "Assign technician" }));
    fireEvent.change(screen.getByLabelText("Search lab technicians"), { target: { value: "Amina" } });
    await screen.findByRole("option", { name: /Amina/ });
    expect(mocks.search).toHaveBeenLastCalledWith("Amina", { test_id: "test-1", visit_id: undefined });
    fireEvent.change(screen.getByLabelText("Lab technician"), { target: { value: "lab-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Save assignment" }));
    expect(await screen.findByText("Assigned to: Amina")).toBeInTheDocument();
    expect(mocks.assign).toHaveBeenCalledWith("test-1", "lab-1");
  });

  it("does not load citizen data for the wrong portal", () => {
    mocks.auth.mockReturnValue({ status: "authenticated", isRequiredPortal: false, claims: { sid: "admin" }, refreshSession: vi.fn() });
    render(<DiagnosticsPage portal="CITIZEN" />);
    expect(screen.getByText("Portal access required")).toBeInTheDocument();
    expect(mocks.citizen).not.toHaveBeenCalled();
  });

  it("shows a retryable role failure instead of an endless spinner", async () => {
    mocks.auth.mockReturnValue({ status: "authenticated", isRequiredPortal: true, claims: { sid: "lab" }, refreshSession: vi.fn() });
    mocks.me.mockRejectedValueOnce(new Error("Unavailable")).mockResolvedValueOnce({ role_code: "LAB_TECHNICIAN", verification_status: "VERIFIED" });
    mocks.professional.mockResolvedValue({ tests: [] });
    render(<DiagnosticsPage portal="PROFESSIONAL" />);
    fireEvent.click(await screen.findByRole("button", { name: "Try again" }));
    await waitFor(() => expect(mocks.professional).toHaveBeenCalled());
    expect(await screen.findByText("No diagnostic tests")).toBeInTheDocument();
  });
});
