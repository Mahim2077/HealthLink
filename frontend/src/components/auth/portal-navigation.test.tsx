import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "@/components/auth/auth-provider";
import { accessTokenStore } from "@/lib/auth/token-store";

const mocks = vi.hoisted(() => ({ logout: vi.fn(), replace: vi.fn() }));
vi.mock("@/lib/auth/actions", () => ({
  logout: mocks.logout,
  logoutAll: vi.fn(),
  refreshSession: vi.fn(),
}));
vi.mock("next/navigation", () => ({
  usePathname: () => "/citizen/doctors/doctor-1",
  useRouter: () => ({ replace: mocks.replace }),
}));

import { PortalNavigation, PortalTextNavigation } from "./portal-navigation";

function citizenToken() {
  const encode = (value: object) => btoa(JSON.stringify(value)).replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");
  const now = Math.floor(Date.now() / 1000);
  return `${encode({ alg: "none" })}.${encode({ exp: now + 1800, iat: now, jti: "j", portal: "CITIZEN", sid: "s", sub: "u", type: "access" })}.x`;
}

describe("PortalNavigation", () => {
  beforeEach(() => {
    accessTokenStore.clear();
    mocks.logout.mockReset();
    mocks.replace.mockReset();
  });

  it("keeps the doctor-search section active on a doctor profile", () => {
    act(() => accessTokenStore.set(citizenToken()));
    render(<AuthProvider><PortalNavigation portal="CITIZEN" /></AuthProvider>);

    expect(screen.getByRole("link", { name: "Find a doctor" })).toHaveAttribute("aria-current", "page");
  });

  it("renders the same citizen destinations as accessible text links", () => {
    render(<PortalTextNavigation portal="CITIZEN" />);

    const navigation = screen.getByRole("navigation", {
      name: "citizen page navigation",
    });
    expect(navigation).toHaveClass("overflow-x-auto");
    expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute(
      "href",
      "/citizen/dashboard",
    );
    expect(screen.getByRole("link", { name: "Find a doctor" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("link", { name: "Appointments" })).toHaveAttribute(
      "href",
      "/citizen/appointments",
    );
    expect(screen.getByRole("link", { name: "My profile" })).toHaveAttribute(
      "href",
      "/citizen/profile",
    );
  });

  it("signs out from the shared portal navigation", async () => {
    act(() => accessTokenStore.set(citizenToken()));
    mocks.logout.mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<AuthProvider><PortalNavigation portal="CITIZEN" /></AuthProvider>);

    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));

    await waitFor(() => expect(mocks.logout).toHaveBeenCalledOnce());
    expect(mocks.replace).toHaveBeenCalledWith("/citizen/login");
  });
});
