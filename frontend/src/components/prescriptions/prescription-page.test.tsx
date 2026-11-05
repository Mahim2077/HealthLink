import { render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { PrescriptionPage } from "./prescription-page";

const { auth, panel } = vi.hoisted(() => ({ auth: vi.fn(), panel: vi.fn() }));
vi.mock("@/components/auth/auth-provider", () => ({ usePortalAuth: auth }));
vi.mock("./prescription-panel", () => ({ PrescriptionPanel: panel }));

beforeEach(() => {
  vi.clearAllMocks();
  auth.mockReturnValue({ status: "authenticated", isRequiredPortal: true,
    claims: { sid: "synthetic-session" }, refreshSession: vi.fn() });
  panel.mockReturnValue(<section aria-label="Prescription content" />);
});

it.each(["CITIZEN", "PROFESSIONAL"] as const)("provides a page heading without changing %s prescription capabilities", (portal) => {
  render(<PrescriptionPage prescriptionId="synthetic-prescription" portal={portal} />);
  expect(screen.getByRole("heading", { level: 1, name: "Prescription" })).toBeInTheDocument();
  expect(screen.getByRole("main")).toHaveAttribute("id", "main-content");
  expect(panel.mock.calls[0][0]).toMatchObject({
    prescriptionId: "synthetic-prescription",
    editable: portal === "PROFESSIONAL",
    autoGeneratePdf: portal === "PROFESSIONAL",
    showAiExplanation: portal === "CITIZEN",
  });
});

it("returns a Citizen to the originating filtered history page", () => {
  render(<PrescriptionPage prescriptionId="synthetic" portal="CITIZEN" returnTo="/citizen/medical-history?resource_type=PRESCRIPTION&page=2" />);
  expect(screen.getByRole("link", { name: "Back" })).toHaveAttribute("href", "/citizen/medical-history?resource_type=PRESCRIPTION&page=2");
});

it.each([undefined, "https://other.example/citizen/medical-history", "//other.example/citizen/medical-history", "/admin/dashboard", "javascript:alert(1)"])("uses a safe direct-entry fallback for %s", (returnTo) => {
  render(<PrescriptionPage prescriptionId="synthetic" portal="CITIZEN" returnTo={returnTo} />);
  expect(screen.getByRole("link", { name: "Back" })).toHaveAttribute("href", "/citizen/appointments");
});

it("never changes the Professional return destination using Citizen query state", () => {
  render(<PrescriptionPage prescriptionId="synthetic" portal="PROFESSIONAL" returnTo="/citizen/medical-history" />);
  expect(screen.getByRole("link", { name: "Back" })).toHaveAttribute("href", "/professional/visits");
});
