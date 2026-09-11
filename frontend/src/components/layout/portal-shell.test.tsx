import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "@/components/auth/auth-provider";
import { accessTokenStore } from "@/lib/auth/token-store";

const mocks = vi.hoisted(() => ({
  loadCitizenMe: vi.fn(),
  replace: vi.fn(),
}));

vi.mock("@/lib/auth/actions", () => ({
  logout: vi.fn(),
  logoutAll: vi.fn(),
  refreshSession: vi.fn(),
}));
vi.mock("@/lib/citizen/api", () => ({
  loadCitizenMe: mocks.loadCitizenMe,
}));
vi.mock("@/lib/professional/api", () => ({
  loadProfessionalMe: vi.fn(),
}));
vi.mock("@/lib/admin/api", () => ({
  loadAdminMe: vi.fn(),
}));
vi.mock("next/navigation", () => ({
  usePathname: () => "/citizen/dashboard",
  useRouter: () => ({ replace: mocks.replace }),
}));

import { PortalShell } from "./portal-shell";

function citizenToken() {
  const encode = (value: object) =>
    btoa(JSON.stringify(value))
      .replace(/=/g, "")
      .replace(/\+/g, "-")
      .replace(/\//g, "_");
  const now = Math.floor(Date.now() / 1000);
  return (
    encode({ alg: "none" }) +
    "." +
    encode({
      exp: now + 1800,
      iat: now,
      jti: "j",
      portal: "CITIZEN",
      sid: "s",
      sub: "u",
      type: "access",
    }) +
    ".x"
  );
}

function renderShell() {
  act(() => accessTokenStore.set(citizenToken()));
  return render(
    <AuthProvider>
      <PortalShell portal="CITIZEN">
        <main>Dashboard content</main>
      </PortalShell>
    </AuthProvider>,
  );
}

describe("PortalShell", () => {
  beforeEach(() => {
    accessTokenStore.clear();
    mocks.loadCitizenMe.mockReset();
    mocks.loadCitizenMe.mockResolvedValue({
      first_name: "Amina",
      last_name: "Rahman",
    });
  });

  it("starts collapsed and expands into a keyboard-resizable navigation", async () => {
    renderShell();
    expect(
      screen.getByRole("navigation", { name: "citizen page navigation" }),
    ).toBeInTheDocument();
    const sidebar = screen.getByLabelText("Citizen portal sidebar");
    expect(sidebar).toHaveStyle({ width: "84px" });

    fireEvent.click(screen.getByRole("button", { name: "Expand navigation" }));
    expect(sidebar).toHaveStyle({ width: "260px" });

    const separator = screen.getByRole("separator", { name: "Resize navigation" });
    expect(separator).toHaveAttribute("tabindex", "0");
    fireEvent.keyDown(separator, { key: "ArrowRight" });
    expect(sidebar).toHaveStyle({ width: "276px" });

    await waitFor(() => expect(screen.getByText("Amina Rahman")).toBeInTheDocument());
    expect(screen.getByRole("link", { name: /Amina Rahman/ })).toHaveAttribute(
      "href",
      "/citizen/profile",
    );
  });

  it("opens and closes the mobile navigation", () => {
    renderShell();
    expect(
      screen.getAllByRole("navigation", { name: "citizen navigation" }),
    ).toHaveLength(1);

    fireEvent.click(screen.getByRole("button", { name: "Open navigation" }));
    expect(
      screen.getAllByRole("navigation", { name: "citizen navigation" }),
    ).toHaveLength(2);

    fireEvent.keyDown(document, { key: "Escape" });
    expect(
      screen.getAllByRole("navigation", { name: "citizen navigation" }),
    ).toHaveLength(1);
  });
});
