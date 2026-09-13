import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { AccessGrantsPage, AccessSession } from "./access-grants-page";
import { SharedPatientsPage } from "./shared-patients-page";

const mocks = vi.hoisted(() => ({ auth: vi.fn(), list: vi.fn(), search: vi.fn(), create: vi.fn(), revoke: vi.fn(), patients: vi.fn(), records: vi.fn() }));
vi.mock("@/components/auth/auth-provider", () => ({ usePortalAuth: mocks.auth }));
vi.mock("@/lib/access/api", async importOriginal => ({ ...await importOriginal<typeof import("@/lib/access/api")>(), listGrants: mocks.list, findDoctors: mocks.search, createGrant: mocks.create, revokeGrant: mocks.revoke, grantedPatients: mocks.patients, sharedRecords: mocks.records }));

beforeEach(() => {
  vi.clearAllMocks();
  mocks.auth.mockReturnValue({ status: "authenticated", isRequiredPortal: true, claims: { sid: "session" }, refreshSession: vi.fn() });
  mocks.list.mockResolvedValue({ grants: [], page: 1, has_next: false });
  mocks.search.mockResolvedValue([{ id: "doctor", name: "Dr Ayesha", designation: "Consultant", facility_name: "City Hospital" }]);
});

it("requires explicit grant confirmation and retains selections after failed save", async () => {
  mocks.create.mockRejectedValue(new Error("Unavailable"));
  render(<AccessGrantsPage />);
  await screen.findByRole("option", { name: /Dr Ayesha/ }, { timeout: 5000 });
  fireEvent.change(screen.getByLabelText("Doctor"), { target: { value: "doctor" } });
  fireEvent.click(screen.getByRole("button", { name: "Review sharing" }));
  expect(mocks.create).not.toHaveBeenCalled();
  expect(screen.getByRole("alertdialog")).toHaveTextContent("Visits only");
  fireEvent.click(screen.getByRole("button", { name: "Confirm" }));
  await screen.findByText(/Unable to save this change/);
  expect(screen.getByLabelText("Doctor")).toHaveValue("doctor");
  expect(mocks.create).toHaveBeenCalledWith({ professional_role_registration_id: "doctor", access_scope: "VISITS_ONLY", expires_at: null });
});

it("confirms soft revocation before sending it", async () => {
  mocks.list.mockResolvedValue({ grants: [{ id: "grant", professional_name: "Dr Ayesha", access_scope: "VISITS_ONLY", expires_at: null, revoked_at: null, active: true }], page: 1, has_next: false });
  mocks.revoke.mockResolvedValue({});
  render(<AccessGrantsPage />);
  fireEvent.click(await screen.findByRole("button", { name: "Revoke access" }));
  expect(mocks.revoke).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Confirm" }));
  await waitFor(() => expect(mocks.revoke).toHaveBeenCalledWith("grant"));
});

it("does not mount private content for wrong portal", () => {
  mocks.auth.mockReturnValue({ status: "authenticated", isRequiredPortal: false, refreshSession: vi.fn() });
  render(<AccessSession portal="CITIZEN"><span>Private records</span></AccessSession>);
  expect(screen.queryByText("Private records")).not.toBeInTheDocument();
});

it("only requests the granted resource type and shows revoked failures", async () => {
  mocks.patients.mockResolvedValue({ grants: [{ id: "grant", citizen_id: "citizen", citizen_name: "Patient", access_scope: "LAB_REPORTS_ONLY", expires_at: null }], page: 1, has_next: false });
  mocks.records.mockRejectedValue(new Error("Revoked"));
  render(<SharedPatientsPage />);
  fireEvent.click(await screen.findByRole("button", { name: "Read shared records" }));
  await screen.findByText(/Records unavailable/);
  expect(mocks.records).toHaveBeenCalledWith("citizen", "LAB_REPORT", 1);
  expect(screen.queryByLabelText("Record type")).not.toBeInTheDocument();
});
