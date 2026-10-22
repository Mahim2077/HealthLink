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
    window.localStorage.clear();
    vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() })));
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
      "/citizen/settings",
    );
  });

  it("contains mobile focus, locks scrolling and restores the opener", () => {
    renderShell();
    expect(
      screen.getAllByRole("navigation", { name: "citizen navigation" }),
    ).toHaveLength(1);

    const opener = screen.getByRole("button", { name: "Open navigation" });
    opener.focus();
    fireEvent.click(opener);
    const dialog = screen.getByRole("dialog");
    expect(dialog).toContainElement(document.activeElement as HTMLElement);
    expect(document.body.style.overflow).toBe("hidden");
    const controls = dialog.querySelectorAll<HTMLElement>('a[href], button:not(:disabled)');
    controls[controls.length - 1].focus();
    fireEvent.keyDown(document, { key: "Tab" });
    expect(controls[0]).toHaveFocus();
    fireEvent.keyDown(document, { key: "Tab", shiftKey: true });
    expect(controls[controls.length - 1]).toHaveFocus();
    expect(
      screen.getAllByRole("navigation", { name: "citizen navigation" }),
    ).toHaveLength(2);

    fireEvent.keyDown(document, { key: "Escape" });
    expect(document.body.style.overflow).toBe("");
    expect(opener).toHaveFocus();
    expect(
      screen.getAllByRole("navigation", { name: "citizen navigation" }),
    ).toHaveLength(1);
  });

  it.each([
    ["CITIZEN", "citizen"],
    ["PROFESSIONAL", "professional"],
    ["ADMIN", "admin"],
  ] as const)("scopes the %s shell to its portal color theme", (portal, theme) => {
    const { container } = render(
      <AuthProvider>
        <PortalShell portal={portal}>
          <main>Portal content</main>
        </PortalShell>
      </AuthProvider>,
    );

    expect(container.firstElementChild).toHaveAttribute("data-portal", theme);
  });
});
