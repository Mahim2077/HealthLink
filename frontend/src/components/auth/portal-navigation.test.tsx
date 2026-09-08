import { act, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "@/components/auth/auth-provider";
import { accessTokenStore } from "@/lib/auth/token-store";

const mocks = vi.hoisted(() => ({ replace: vi.fn() }));
vi.mock("@/lib/auth/actions", () => ({
  logout: vi.fn(),
  logoutAll: vi.fn(),
  refreshSession: vi.fn(),
}));
vi.mock("next/navigation", () => ({
  usePathname: () => "/citizen/doctors/doctor-1",
  useRouter: () => ({ replace: mocks.replace }),
}));

import { PortalNavigation } from "./portal-navigation";

function citizenToken() {
  const encode = (value: object) => btoa(JSON.stringify(value)).replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");
  const now = Math.floor(Date.now() / 1000);
  return `${encode({ alg: "none" })}.${encode({ exp: now + 1800, iat: now, jti: "j", portal: "CITIZEN", sid: "s", sub: "u", type: "access" })}.x`;
}

describe("PortalNavigation", () => {
  beforeEach(() => {
    accessTokenStore.clear();
    mocks.replace.mockReset();
  });

  it("keeps the doctor-search section active on a doctor profile", () => {
    act(() => accessTokenStore.set(citizenToken()));
    render(<AuthProvider><PortalNavigation portal="CITIZEN" /></AuthProvider>);

    expect(screen.getByRole("link", { name: "Find a doctor" })).toHaveAttribute("aria-current", "page");
  });
});
