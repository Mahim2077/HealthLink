import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  correctCitizenIdentity: vi.fn(),
  loadCitizenIdentity: vi.fn(),
  logout: vi.fn(),
  refreshSession: vi.fn(),
  replace: vi.fn(),
}));
vi.mock("@/components/admin/admin-portal-guard", () => ({
  AdminPortalGuard: ({ children }: { children: React.ReactNode }) => children,
}));
vi.mock("@/lib/auth/actions", () => ({
  logout: mocks.logout,
  logoutAll: vi.fn(),
  refreshSession: mocks.refreshSession,
  replaceSession: vi.fn(),
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: mocks.replace }) }));
vi.mock("@/lib/admin/api", () => ({
  correctCitizenIdentity: mocks.correctCitizenIdentity,
  loadCitizenIdentity: mocks.loadCitizenIdentity,
  searchCitizenIdentities: vi.fn(),
}));

import { CitizenIdentityDetail } from "./citizen-identity-detail";

const baseDetail = {
  address: "Dhaka",
  auth_session_count: 2,
  birth_certificate_number: "BCN-ORIG",
  blood_group: "B+",
  date_of_birth: "1990-01-01",
  email: "alice@example.com",
  first_name: "Alice",
  gender: "female",
  identity_created_at: "2026-08-10T10:00:00Z",
  identity_updated_at: "2026-08-10T10:00:00Z",
  is_active: true,
  last_name: "Citizen",
  nid_number: "1234567890",
  registered_with: "NID" as const,
  user_id: "11111111-1111-1111-1111-111111111111",
};

describe("CitizenIdentityDetail", () => {
  beforeEach(() => {
    mocks.loadCitizenIdentity.mockReset();
    mocks.correctCitizenIdentity.mockReset();
    mocks.logout.mockReset();
    mocks.refreshSession.mockReset();
    mocks.replace.mockReset();
    mocks.loadCitizenIdentity.mockResolvedValue(baseDetail);
  });

  it("loads the identity record and links back to the search page", async () => {
    render(<CitizenIdentityDetail userId={baseDetail.user_id} />);

    expect(await screen.findByText("Alice Citizen")).toBeInTheDocument();
    expect(screen.getByText("BCN-ORIG")).toBeInTheDocument();
    expect(screen.getByText("1234567890")).toBeInTheDocument();
    expect(screen.getByText("female")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "← Identity search" })).toHaveAttribute(
      "href",
      "/admin/citizen-identities",
    );
    await waitFor(() => expect(mocks.loadCitizenIdentity).toHaveBeenCalledWith(baseDetail.user_id));
  });

  it("swaps the new value source when the correction type radio toggles to BCN", async () => {
    render(<CitizenIdentityDetail userId={baseDetail.user_id} />);
    await screen.findByText("Alice Citizen");

    fireEvent.click(screen.getByLabelText("Birth Certificate Number"));

    await waitFor(() => {
      const value = (screen.getByLabelText("New value") as HTMLInputElement).value;
      expect(value).toBe("BCN-ORIG");
    });
  });

  it("submits the correction request and refreshes the identity", async () => {
    mocks.correctCitizenIdentity.mockResolvedValue({
      audit_log_id: "audit-abcdef1234567890",
      correction_type: "NID",
      user_id: baseDetail.user_id,
    });
    mocks.loadCitizenIdentity
      .mockResolvedValueOnce(baseDetail)
      .mockResolvedValueOnce({ ...baseDetail, nid_number: "9999999999" });

    render(<CitizenIdentityDetail userId={baseDetail.user_id} />);
    await screen.findByText("Alice Citizen");

    fireEvent.change(screen.getByLabelText("New value"), { target: { value: " 9999999999 " } });
    fireEvent.change(screen.getByLabelText("Reason (recorded in audit log)"), {
      target: { value: "Operator typo." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Record correction" }));

    await waitFor(() =>
      expect(mocks.correctCitizenIdentity).toHaveBeenCalledWith(baseDetail.user_id, {
        correction_type: "NID",
        new_value: "9999999999",
        reason: "Operator typo.",
      }),
    );
    expect(await screen.findByText(/Recorded NID correction/)).toBeInTheDocument();
    expect(await screen.findByText("9999999999")).toBeInTheDocument();
  });

  it("requires a reason before submitting", async () => {
    render(<CitizenIdentityDetail userId={baseDetail.user_id} />);
    await screen.findByText("Alice Citizen");

    fireEvent.change(screen.getByLabelText("New value"), { target: { value: "9999999999" } });
    fireEvent.change(screen.getByLabelText("Reason (recorded in audit log)"), {
      target: { value: "   " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Record correction" }));

    expect(await screen.findByText("A reason is required for audit.")).toBeInTheDocument();
    expect(mocks.correctCitizenIdentity).not.toHaveBeenCalled();
  });

  it("surfaces an error from the api and offers a retry", async () => {
    mocks.loadCitizenIdentity.mockRejectedValueOnce(new Error("nope"));
    render(<CitizenIdentityDetail userId={baseDetail.user_id} />);

    expect(await screen.findByText("Identity unavailable")).toBeInTheDocument();
    mocks.loadCitizenIdentity.mockResolvedValueOnce(baseDetail);
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    });
    expect(await screen.findByText("Alice Citizen")).toBeInTheDocument();
  });
});