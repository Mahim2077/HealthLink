import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "@/components/auth/auth-provider";
import { ApiError } from "@/lib/api/errors";
import { accessTokenStore } from "@/lib/auth/token-store";
import type { Portal } from "@/lib/auth/types";
import type { CitizenDashboardData } from "@/lib/citizen/types";

import { CitizenDashboard } from "./citizen-dashboard";

const testMocks = vi.hoisted(() => ({
  logout: vi.fn(),
  logoutAll: vi.fn(),
  refreshSession: vi.fn(),
  replace: vi.fn(),
  replaceSession: vi.fn(),
}));

vi.mock("@/lib/auth/actions", () => ({
  logout: testMocks.logout,
  logoutAll: testMocks.logoutAll,
  refreshSession: testMocks.refreshSession,
  replaceSession: testMocks.replaceSession,
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: testMocks.replace }),
}));

const dashboardData: CitizenDashboardData = {
  identity: {
    birth_certificate_number: null,
    nid_added_at: null,
    nid_number: "00123456789012345",
    registered_with: "NID",
  },
  profile: {
    address: "Dhaka",
    blood_group: "O+",
    citizen_id: "citizen-1",
    created_at: "2026-08-10T08:00:00Z",
    date_of_birth: "1992-05-14",
    email: "amina@example.com",
    first_name: "Amina",
    gender: "FEMALE",
    last_name: "Rahman",
    updated_at: "2026-08-10T08:00:00Z",
    user_id: "user-1",
  },
};

function createToken(portal: Portal, expiresInSeconds = 1800): string {
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
      exp: issuedAt + expiresInSeconds,
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

function renderDashboard(loadAction = vi.fn().mockResolvedValue(dashboardData)) {
  return {
    loadAction,
    ...render(
      <AuthProvider>
        <CitizenDashboard loadAction={loadAction} />
      </AuthProvider>,
    ),
  };
}

describe("CitizenDashboard", () => {
  beforeEach(() => {
    accessTokenStore.clear();
    testMocks.logout.mockReset();
    testMocks.logoutAll.mockReset();
    testMocks.refreshSession.mockReset();
    testMocks.replace.mockReset();
    testMocks.replaceSession.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("restores a Citizen session after reload, loads both dashboard resources, and masks identity", async () => {
    const citizenToken = createToken("CITIZEN");
    let resolveRefresh!: () => void;
    testMocks.refreshSession.mockImplementation(
      () =>
        new Promise<string>((resolve) => {
          resolveRefresh = () => {
            accessTokenStore.set(citizenToken);
            resolve(citizenToken);
          };
        }),
    );
    const { loadAction } = renderDashboard();

    expect(
      screen.getByText("Checking your Citizen session"),
    ).toBeInTheDocument();
    await act(async () => resolveRefresh());
    expect(await screen.findByText("Welcome, Amina.")).toBeInTheDocument();
    expect(testMocks.refreshSession).toHaveBeenCalledOnce();
    expect(loadAction).toHaveBeenCalledOnce();
    expect(screen.getByTestId("masked-identity")).toHaveTextContent("2345");
    expect(screen.queryByText("00123456789012345")).not.toBeInTheDocument();
  });

  it("does not load citizen data for a different portal token", () => {
    act(() => accessTokenStore.set(createToken("PROFESSIONAL")));
    const { loadAction } = renderDashboard();

    expect(
      screen.getByText("Citizen Portal access required"),
    ).toBeInTheDocument();
    expect(loadAction).not.toHaveBeenCalled();
    expect(testMocks.refreshSession).not.toHaveBeenCalled();
  });

  it("shows the sign-in guard when cookie hydration fails", async () => {
    testMocks.refreshSession.mockRejectedValue(
      new ApiError(401, "Session expired."),
    );
    const { loadAction } = renderDashboard();

    expect(await screen.findByText("Sign in to continue")).toBeInTheDocument();
    expect(loadAction).not.toHaveBeenCalled();
    expect(
      screen.getByRole("link", { name: "Sign in to Citizen Portal" }),
    ).toHaveAttribute("href", "/citizen/login");
  });

  it("shows protected hydration, not signed-out UI, while an idle token is refreshed", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2030-01-01T00:00:00.000Z"));
    act(() => accessTokenStore.set(createToken("CITIZEN", 2)));

    const refreshedToken = createToken("CITIZEN", 1800);
    let resolveRefresh!: () => void;
    testMocks.refreshSession.mockImplementation(
      () =>
        new Promise<string>((resolve) => {
          resolveRefresh = () => {
            accessTokenStore.set(refreshedToken);
            resolve(refreshedToken);
          };
        }),
    );
    renderDashboard();
    await act(async () => {
      await Promise.resolve();
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2_000);
    });

    expect(
      screen.getByText("Checking your Citizen session"),
    ).toBeInTheDocument();
    expect(screen.queryByText("Sign in to continue")).not.toBeInTheDocument();
    expect(testMocks.refreshSession).toHaveBeenCalledOnce();

    await act(async () => resolveRefresh());
    expect(screen.getByText("Welcome, Amina.")).toBeInTheDocument();
  });

  it("shows a data error and retries the citizen dashboard request", async () => {
    act(() => accessTokenStore.set(createToken("CITIZEN")));
    const loadAction = vi
      .fn()
      .mockRejectedValueOnce(new ApiError(503, "Citizen service unavailable."))
      .mockResolvedValueOnce(dashboardData);
    renderDashboard(loadAction);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Citizen service unavailable.",
    );
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));

    expect(await screen.findByText("Welcome, Amina.")).toBeInTheDocument();
    expect(loadAction).toHaveBeenCalledTimes(2);
  });

  it("logs out, clears the dashboard, and never bootstraps a new session", async () => {
    act(() => accessTokenStore.set(createToken("CITIZEN")));
    testMocks.logout.mockImplementation(async () => {
      accessTokenStore.clear();
    });
    renderDashboard();
    await screen.findByText("Welcome, Amina.");

    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));

    await waitFor(() => expect(testMocks.logout).toHaveBeenCalledOnce());
    expect(testMocks.replace).toHaveBeenCalledWith("/citizen/login");
    expect(testMocks.refreshSession).not.toHaveBeenCalled();
    expect(screen.getByText("Sign in to continue")).toBeInTheDocument();
  });
});
