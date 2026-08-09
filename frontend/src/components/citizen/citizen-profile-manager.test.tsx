import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi, type Mock } from "vitest";

import { AuthProvider } from "@/components/auth/auth-provider";
import { ApiError } from "@/lib/api/errors";
import { accessTokenStore } from "@/lib/auth/token-store";
import type { CitizenDashboardData } from "@/lib/citizen/types";

import { CitizenProfileManager } from "./citizen-profile-manager";

const mocks = vi.hoisted(() => ({ refreshSession: vi.fn() }));

vi.mock("@/lib/auth/actions", () => ({
  logout: vi.fn(),
  logoutAll: vi.fn(),
  refreshSession: mocks.refreshSession,
  replaceSession: vi.fn(),
}));

const data: CitizenDashboardData = {
  identity: {
    birth_certificate_number: "BCN-2001-00001",
    nid_added_at: null,
    nid_number: null,
    registered_with: "BCN",
  },
  profile: {
    address: "Dhaka",
    blood_group: "A+",
    citizen_id: "citizen-1",
    created_at: "2026-08-10T08:00:00Z",
    date_of_birth: "1995-05-20",
    email: "amina@example.com",
    first_name: "Amina",
    gender: "FEMALE",
    last_name: "Rahman",
    updated_at: "2026-08-10T08:00:00Z",
    user_id: "user-1",
  },
};

function token(portal: "CITIZEN" | "ADMIN" = "CITIZEN") {
  const encode = (value: object) =>
    btoa(JSON.stringify(value)).replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");
  const now = Math.floor(Date.now() / 1000);
  return `${encode({ alg: "none" })}.${encode({ exp: now + 1800, iat: now, jti: "jti", portal, sid: "sid", sub: "user-1", type: "access" })}.x`;
}

function renderManager(options: {
  saveAction?: Mock<(request: Parameters<NonNullable<React.ComponentProps<typeof CitizenProfileManager>["saveAction"]>>[0]) => Promise<Awaited<ReturnType<NonNullable<React.ComponentProps<typeof CitizenProfileManager>["saveAction"]>>>>>;
  addAction?: Mock<(request: Parameters<NonNullable<React.ComponentProps<typeof CitizenProfileManager>["addAction"]>>[0]) => Promise<Awaited<ReturnType<NonNullable<React.ComponentProps<typeof CitizenProfileManager>["addAction"]>>>>>;
  loadAction?: Mock<() => Promise<CitizenDashboardData>>;
} = {}) {
  const loadAction = options.loadAction ?? vi.fn().mockResolvedValue(data);
  const saveAction = options.saveAction ?? vi.fn().mockResolvedValue(data.profile);
  const addAction = options.addAction ?? vi.fn();
  render(
    <AuthProvider>
      <CitizenProfileManager
        addAction={addAction}
        loadAction={loadAction}
        saveAction={saveAction}
      />
    </AuthProvider>,
  );
  return { addAction, loadAction, saveAction };
}

describe("CitizenProfileManager", () => {
  beforeEach(() => {
    accessTokenStore.clear();
    mocks.refreshSession.mockReset();
  });

  it("updates only profile fields without any identity mutation", async () => {
    act(() => accessTokenStore.set(token()));
    const updated = {
      ...data.profile,
      address: "Chattogram",
      first_name: "Ayesha",
      last_name: "Karim",
    };
    const saveAction = vi.fn().mockResolvedValue(updated);
    const { addAction } = renderManager({ saveAction });
    await screen.findByRole("heading", { name: "Profile and identity" });

    fireEvent.change(screen.getByLabelText(/First name/), { target: { value: " Ayesha " } });
    fireEvent.change(screen.getByLabelText(/Last name/), { target: { value: " Karim " } });
    fireEvent.change(screen.getByLabelText("Address"), { target: { value: " Chattogram " } });
    fireEvent.click(screen.getByRole("button", { name: "Save profile" }));

    await waitFor(() => expect(saveAction).toHaveBeenCalledOnce());
    expect(saveAction.mock.calls[0][0]).toEqual({
      address: "Chattogram",
      blood_group: "A+",
      date_of_birth: "1995-05-20",
      first_name: "Ayesha",
      gender: "FEMALE",
      last_name: "Karim",
    });
    expect(saveAction.mock.calls[0][0]).not.toHaveProperty("nid_number");
    expect(addAction).not.toHaveBeenCalled();
    expect(await screen.findByText("Your profile has been updated.")).toBeInTheDocument();
  });

  it("requires exact CONFIRM before adding NID and locks replacement after success", async () => {
    act(() => accessTokenStore.set(token()));
    const addAction = vi.fn().mockResolvedValue({
      ...data.identity,
      nid_added_at: "2026-08-10T10:00:00Z",
      nid_number: "NID-90001",
    });
    renderManager({ addAction });
    await screen.findByRole("heading", { name: "Add your National ID" });

    fireEvent.change(screen.getByLabelText(/National ID/), { target: { value: "NID-90001" } });
    fireEvent.change(screen.getByLabelText(/Type "CONFIRM"/), { target: { value: "confirm" } });
    fireEvent.click(screen.getByRole("button", { name: "Add National ID permanently" }));
    expect(addAction).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("Type CONFIRM exactly");

    fireEvent.change(screen.getByLabelText(/Type "CONFIRM"/), { target: { value: "CONFIRM" } });
    fireEvent.click(screen.getByRole("button", { name: "Add National ID permanently" }));
    await waitFor(() => expect(addAction).toHaveBeenCalledWith({ confirmation: "CONFIRM", nid_number: "NID-90001" }));
    expect(screen.queryByRole("button", { name: "Add National ID permanently" })).not.toBeInTheDocument();
    expect(screen.getByText(/Your National ID was added/)).toBeInTheDocument();
    expect(screen.getAllByText(/0001/).length).toBeGreaterThan(0);
  });

  it("keeps the one-time form available when the server rejects a duplicate NID", async () => {
    act(() => accessTokenStore.set(token()));
    const addAction = vi.fn().mockRejectedValue(new ApiError(409, "NID is already registered."));
    renderManager({ addAction });
    await screen.findByRole("heading", { name: "Add your National ID" });
    fireEvent.change(screen.getByLabelText(/National ID/), { target: { value: "DUPLICATE" } });
    fireEvent.change(screen.getByLabelText(/Type "CONFIRM"/), { target: { value: "CONFIRM" } });
    fireEvent.click(screen.getByRole("button", { name: "Add National ID permanently" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("NID is already registered.");
    expect(screen.getByRole("button", { name: "Add National ID permanently" })).toBeInTheDocument();
  });

  it("does not load private data for a wrong-portal session", () => {
    act(() => accessTokenStore.set(token("ADMIN")));
    const { loadAction } = renderManager();
    expect(screen.getByText("Citizen Portal access required")).toBeInTheDocument();
    expect(loadAction).not.toHaveBeenCalled();
  });
});
