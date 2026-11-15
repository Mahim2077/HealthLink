import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/errors";
import { AuthProvider } from "./auth-provider";
import { PortalLoginGate } from "./portal-login-gate";

const mocks = vi.hoisted(() => ({
  router: { replace: vi.fn() },
  refresh: vi.fn(),
  loadProfessionalMe: vi.fn(),
}));

vi.mock("next/navigation", () => ({ useRouter: () => mocks.router }));
vi.mock("@/lib/auth/actions", () => ({ refreshSession: mocks.refresh, logout: vi.fn(), logoutAll: vi.fn() }));
vi.mock("@/lib/professional/api", () => ({ loadProfessionalMe: mocks.loadProfessionalMe }));

function openLogin(portal: "CITIZEN" | "PROFESSIONAL") {
  render(
    <AuthProvider>
      <PortalLoginGate portal={portal}><form aria-label="Sign in" /></PortalLoginGate>
    </AuthProvider>,
  );
}

describe("PortalLoginGate", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    window.history.replaceState(null, "", "/");
  });

  it("shows only the requested portal's form when its session is missing", async () => {
    mocks.refresh.mockRejectedValue(new ApiError(401, "No session"));
    openLogin("CITIZEN");
    expect(await screen.findByRole("form", { name: "Sign in" })).toBeVisible();
    expect(mocks.refresh).toHaveBeenCalledWith("CITIZEN");
    expect(mocks.router.replace).not.toHaveBeenCalled();
  });

  it("resumes a Citizen session and keeps a safe return destination", async () => {
    window.history.replaceState(null, "", "/citizen/login?returnTo=%2Fcitizen%2Fmedical-history");
    mocks.refresh.mockResolvedValue("active-token");
    openLogin("CITIZEN");
    await waitFor(() => expect(mocks.router.replace).toHaveBeenCalledWith("/citizen/medical-history"));
    expect(screen.queryByRole("form")).not.toBeInTheDocument();
  });

  it.each([
    ["VERIFIED", "/professional/dashboard"],
    ["PENDING", "/professional/status"],
    ["REJECTED", "/professional/status"],
  ])("resumes a %s professional session at its allowed destination", async (verification_status, destination) => {
    mocks.refresh.mockResolvedValue("active-token");
    mocks.loadProfessionalMe.mockResolvedValue({ verification_status });
    openLogin("PROFESSIONAL");
    await waitFor(() => expect(mocks.router.replace).toHaveBeenCalledWith(destination));
    expect(mocks.refresh).toHaveBeenCalledWith("PROFESSIONAL");
    expect(screen.queryByRole("form")).not.toBeInTheDocument();
  });

  it("allows a retry when the session check temporarily fails", async () => {
    mocks.refresh.mockRejectedValueOnce(new TypeError("Network unavailable"));
    mocks.refresh.mockResolvedValueOnce("active-token");
    openLogin("CITIZEN");
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not check your session");
    expect(screen.queryByRole("form")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(mocks.router.replace).toHaveBeenCalledWith("/citizen/dashboard"));
  });
});
