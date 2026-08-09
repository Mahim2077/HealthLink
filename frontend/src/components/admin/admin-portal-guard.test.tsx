import { act, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "@/components/auth/auth-provider";
import { ApiError } from "@/lib/api/errors";
import { accessTokenStore } from "@/lib/auth/token-store";

const mocks = vi.hoisted(() => ({ loadRegistrations: vi.fn(), refreshSession: vi.fn() }));
vi.mock("@/lib/admin/api", () => ({ loadProfessionalRegistrations: mocks.loadRegistrations }));
vi.mock("@/lib/auth/actions", () => ({ logout: vi.fn(), logoutAll: vi.fn(), refreshSession: mocks.refreshSession, replaceSession: vi.fn() }));

import { ProfessionalVerificationQueue } from "./professional-verification-queue";

function token(portal: "ADMIN" | "CITIZEN") {
  const encode = (value: object) => btoa(JSON.stringify(value)).replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");
  const now = Math.floor(Date.now() / 1000);
  return `${encode({ alg: "none" })}.${encode({ exp: now + 1800, iat: now, jti: "j", portal, sid: "s", sub: "u", type: "access" })}.x`;
}

describe("AdminPortalGuard", () => {
  beforeEach(() => { accessTokenStore.clear(); mocks.loadRegistrations.mockReset(); mocks.refreshSession.mockReset(); mocks.loadRegistrations.mockResolvedValue([]); });

  it("does not mount private queue data under a different portal", () => {
    act(() => accessTokenStore.set(token("CITIZEN")));
    render(<AuthProvider><ProfessionalVerificationQueue /></AuthProvider>);
    expect(screen.getByText("Admin Portal access required")).toBeInTheDocument();
    expect(mocks.loadRegistrations).not.toHaveBeenCalled();
  });

  it("does not mount private queue data after failed cookie hydration", async () => {
    mocks.refreshSession.mockRejectedValue(new ApiError(401, "Expired"));
    render(<AuthProvider><ProfessionalVerificationQueue /></AuthProvider>);
    expect(await screen.findByText("Admin sign in required")).toBeInTheDocument();
    expect(mocks.loadRegistrations).not.toHaveBeenCalled();
  });

  it("mounts private queue data only after ADMIN authorization", async () => {
    act(() => accessTokenStore.set(token("ADMIN")));
    render(<AuthProvider><ProfessionalVerificationQueue /></AuthProvider>);
    expect(await screen.findByText("Queue is clear")).toBeInTheDocument();
    expect(mocks.loadRegistrations).toHaveBeenCalledWith("PENDING");
  });
});
