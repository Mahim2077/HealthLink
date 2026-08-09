import { act, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "@/components/auth/auth-provider";
import { accessTokenStore } from "@/lib/auth/token-store";

import { ProfessionalOnboarding } from "./professional-onboarding";

const mocks = vi.hoisted(() => ({ refreshSession: vi.fn() }));

vi.mock("@/lib/auth/actions", () => ({
  logout: vi.fn(),
  logoutAll: vi.fn(),
  refreshSession: mocks.refreshSession,
  replaceSession: vi.fn(),
}));

function token(portal: "CITIZEN" | "ADMIN") {
  const encode = (value: object) => btoa(JSON.stringify(value)).replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");
  const now = Math.floor(Date.now() / 1000);
  return `${encode({ alg: "none" })}.${encode({ exp: now + 1800, iat: now, jti: "jti", portal, sid: "sid", sub: "user", type: "access" })}.x`;
}

describe("ProfessionalOnboarding", () => {
  beforeEach(() => {
    accessTokenStore.clear();
    mocks.refreshSession.mockReset();
  });

  it("hydrates an existing citizen session before showing protected onboarding", async () => {
    mocks.refreshSession.mockImplementation(async () => {
      const value = token("CITIZEN");
      accessTokenStore.set(value);
      return value;
    });
    render(<AuthProvider><ProfessionalOnboarding /></AuthProvider>);
    expect(await screen.findByRole("button", { name: "Submit role for verification" })).toBeInTheDocument();
    expect(screen.queryByLabelText(/Email address/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/^National ID/)).not.toBeInTheDocument();
  });

  it("shows a sign-in guard when cookie hydration fails", async () => {
    mocks.refreshSession.mockRejectedValue(new Error("No session"));
    render(<AuthProvider><ProfessionalOnboarding /></AuthProvider>);
    expect(await screen.findByText("Sign in before onboarding")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in as a citizen" })).toHaveAttribute("href", "/citizen/login");
  });

  it("rejects a valid token from the wrong portal before rendering private onboarding", () => {
    act(() => accessTokenStore.set(token("ADMIN")));
    render(<AuthProvider><ProfessionalOnboarding /></AuthProvider>);
    expect(screen.getByText("Citizen session required")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Submit role for verification" })).not.toBeInTheDocument();
  });
});
