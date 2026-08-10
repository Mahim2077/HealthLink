import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  logout: vi.fn(),
  refreshSession: vi.fn(),
  replace: vi.fn(),
  searchCitizenIdentities: vi.fn(),
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
  searchCitizenIdentities: mocks.searchCitizenIdentities,
  loadCitizenIdentity: vi.fn(),
  correctCitizenIdentity: vi.fn(),
}));

import { CitizenIdentitySupport } from "./citizen-identity-support";

const baseRow = {
  birth_certificate_number: null,
  email: "alice@example.com",
  first_name: "Alice",
  identity_created_at: "2026-08-10T10:00:00Z",
  identity_updated_at: "2026-08-10T10:00:00Z",
  is_active: true,
  last_name: "Citizen",
  nid_number: "1234567890",
  registered_with: "NID" as const,
  user_id: "11111111-1111-1111-1111-111111111111",
};

describe("CitizenIdentitySupport", () => {
  beforeEach(() => {
    mocks.logout.mockReset();
    mocks.refreshSession.mockReset();
    mocks.replace.mockReset();
    mocks.searchCitizenIdentities.mockReset();
    mocks.searchCitizenIdentities.mockResolvedValue([baseRow]);
  });

  it("loads the initial workspace and renders a row with a link to the detail page", async () => {
    render(<CitizenIdentitySupport />);

    expect(await screen.findByText("Alice Citizen")).toBeInTheDocument();
    expect(screen.getByText("alice@example.com")).toBeInTheDocument();
    expect(screen.getByText("1234567890")).toBeInTheDocument();
    expect(screen.getByText("ACTIVE")).toBeInTheDocument();
    expect(screen.getByText("Registered via NID")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open identity" })).toHaveAttribute(
      "href",
      "/admin/citizen-identities/11111111-1111-1111-1111-111111111111",
    );
    await waitFor(() =>
      expect(mocks.searchCitizenIdentities).toHaveBeenCalledWith(expect.objectContaining({ limit: 50 })),
    );
  });

  it("submits trimmed filters and forwards them to the search api", async () => {
    render(<CitizenIdentitySupport />);
    await screen.findByText("Alice Citizen");

    fireEvent.change(screen.getByLabelText("National ID (NID)"), { target: { value: "  9876543210  " } });
    fireEvent.click(screen.getByRole("button", { name: "Search identities" }));

    await waitFor(() =>
      expect(mocks.searchCitizenIdentities).toHaveBeenCalledWith({
        birth_certificate_number: "",
        email: "",
        limit: 50,
        nid_number: "9876543210",
        user_id: "",
      }),
    );
  });

  it("rejects an empty filter set without calling the api", async () => {
    mocks.searchCitizenIdentities.mockClear();
    render(<CitizenIdentitySupport />);
    await screen.findByText("Alice Citizen");
    mocks.searchCitizenIdentities.mockClear();

    fireEvent.click(screen.getByRole("button", { name: "Search identities" }));

    expect(
      await screen.findByText("Provide at least one of NID, Birth Certificate Number, email, or User ID."),
    ).toBeInTheDocument();
    expect(mocks.searchCitizenIdentities).not.toHaveBeenCalled();
  });

  it("surfaces an empty state when no rows match", async () => {
    mocks.searchCitizenIdentities.mockResolvedValue([]);
    render(<CitizenIdentitySupport />);

    expect(await screen.findByText("No matches found")).toBeInTheDocument();
    expect(screen.getByText("No citizen identity matched these filters.")).toBeInTheDocument();
  });

  it("renders an error banner and recovers via the retry action", async () => {
    mocks.searchCitizenIdentities
      .mockRejectedValueOnce(new Error("boom"))
      .mockResolvedValueOnce([baseRow]);
    render(<CitizenIdentitySupport />);

    expect(await screen.findByText("Identity search unavailable")).toBeInTheDocument();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    });

    expect(await screen.findByText("Alice Citizen")).toBeInTheDocument();
  });
});