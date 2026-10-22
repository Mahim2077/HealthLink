import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { SettingsLayout } from "./settings-layout";
import { AccountSettings } from "./account-settings";
import { PracticeSettings } from "./practice-settings";
import { SecuritySettings } from "./security-settings";

const mocks = vi.hoisted(() => ({ auth: vi.fn(), me: vi.fn(), admin: vi.fn(), refresh: vi.fn(), logout: vi.fn(), logoutAll: vi.fn(), replace: vi.fn() }));
vi.mock("@/components/auth/auth-provider", () => ({ usePortalAuth: mocks.auth }));
vi.mock("@/lib/professional/api", () => ({ loadProfessionalMe: mocks.me }));
vi.mock("@/lib/admin/api", () => ({ loadAdminMe: mocks.admin }));
vi.mock("next/navigation", () => ({ usePathname: () => "/professional/settings", useRouter: () => ({ replace: mocks.replace }) }));
vi.mock("@/components/citizen/citizen-profile-manager", () => ({ CitizenProfileManager: ({ embedded }: { embedded: boolean }) => <p>{embedded ? "Embedded profile" : "Standalone profile"}</p> }));
vi.mock("@/components/professional/practice-schedule-editor", () => ({ PracticeScheduleEditor: () => <p>Schedule editor</p> }));
const doctor = { first_name: "Amina", last_name: "Rahman", email: "test@example.com", role_code: "DOCTOR", role_name: "Doctor", designation: "Doctor", verification_status: "VERIFIED", facility: { name: "Test clinic" } };
beforeEach(() => {
  vi.clearAllMocks();
  mocks.auth.mockReturnValue({ status: "authenticated", isRequiredPortal: true, claims: { sid: "session1" }, refreshSession: mocks.refresh, logout: mocks.logout, logoutAll: mocks.logoutAll });
  mocks.me.mockResolvedValue(doctor);
  mocks.admin.mockResolvedValue({ ...doctor, is_super_admin: false });
  vi.spyOn(window, "confirm").mockReturnValue(true);
});
it("shows doctor-specific settings and the verified facility without editing controls", async () => {
  render(<SettingsLayout portal="PROFESSIONAL"><AccountSettings /></SettingsLayout>);
  expect(await screen.findByText("Test clinic")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Practice hours/ })).toHaveAttribute("href", "/professional/settings/practice");
  expect(screen.queryByRole("textbox")).toBeNull();
});
it.each([["LAB_TECHNICIAN", "VERIFIED"], ["DOCTOR", "PENDING"], ["DOCTOR", "REJECTED"]])("denies the practice editor for %s %s", async (role, status) => {
  mocks.me.mockResolvedValue({ ...doctor, role_code: role, verification_status: status });
  render(<SettingsLayout portal="PROFESSIONAL"><PracticeSettings /></SettingsLayout>);
  expect(await screen.findByRole("heading", { name: "Verified doctor access required" })).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: /Practice hours/ })).toBeNull();
  expect(screen.queryByText("Schedule editor")).toBeNull();
});
it("gates wrong-portal sessions without fetching any account", () => {
  mocks.auth.mockReturnValue({ status: "authenticated", isRequiredPortal: false });
  render(<SettingsLayout portal="PROFESSIONAL"><AccountSettings /></SettingsLayout>);
  expect(screen.getByText("Portal access required")).toBeInTheDocument();
  expect(mocks.me).not.toHaveBeenCalled(); expect(mocks.admin).not.toHaveBeenCalled();
});
it("offers sign-in after session recovery fails", async () => {
  mocks.auth.mockReturnValue({ status: "unauthenticated", refreshSession: mocks.refresh });
  mocks.refresh.mockRejectedValueOnce(new Error("expired"));
  render(<SettingsLayout portal="ADMIN"><AccountSettings /></SettingsLayout>);
  expect(await screen.findByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/admin/login");
  expect(mocks.admin).not.toHaveBeenCalled();
});
it("retries failed account loading", async () => {
  mocks.me.mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce(doctor);
  render(<SettingsLayout portal="PROFESSIONAL"><AccountSettings /></SettingsLayout>);
  fireEvent.click(await screen.findByRole("button", { name: "Try again" }));
  expect(await screen.findByText("Test clinic")).toBeInTheDocument();
});
it("uses citizen profile inside Settings without nesting another main", async () => {
  render(<SettingsLayout portal="CITIZEN"><AccountSettings /></SettingsLayout>);
  expect(await screen.findByText("Embedded profile")).toBeInTheDocument();
  expect(screen.getAllByRole("main")).toHaveLength(1);
  expect(screen.getByRole("link", { name: /Privacy & sharing/ })).toBeInTheDocument();
});
it("shows only the administrator's own read-only account", async () => {
  render(<SettingsLayout portal="ADMIN"><AccountSettings /></SettingsLayout>);
  expect(await screen.findByText("Administrator", { exact: true })).toBeInTheDocument();
  expect(mocks.me).not.toHaveBeenCalled();
  expect(screen.queryByRole("link", { name: /Practice hours|Privacy & sharing/ })).toBeNull();
});
it.each(["current", "all"])("confirms and performs %s session sign-out", async scope => {
  render(<SettingsLayout portal="PROFESSIONAL"><SecuritySettings /></SettingsLayout>);
  const button = await screen.findByRole("button", { name: scope === "all" ? "Sign out all sessions" : "Sign out" });
  fireEvent.click(button);
  await waitFor(() => expect(scope === "all" ? mocks.logoutAll : mocks.logout).toHaveBeenCalledOnce());
  expect(mocks.replace).toHaveBeenCalledWith("/professional/login");
  if (scope === "all") expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining("other portals"));
});
it("cancels all-session sign-out and keeps the session", async () => {
  vi.mocked(window.confirm).mockReturnValue(false);
  render(<SettingsLayout portal="ADMIN"><SecuritySettings /></SettingsLayout>);
  fireEvent.click(await screen.findByRole("button", { name: "Sign out all sessions" }));
  expect(mocks.logoutAll).not.toHaveBeenCalled(); expect(mocks.replace).not.toHaveBeenCalled();
});
it("retains error feedback and permits retry when logout fails", async () => {
  mocks.logoutAll.mockRejectedValueOnce(new Error("offline"));
  render(<SettingsLayout portal="ADMIN"><SecuritySettings /></SettingsLayout>);
  fireEvent.click(await screen.findByRole("button", { name: "Sign out all sessions" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Please try again");
  expect(mocks.replace).not.toHaveBeenCalled();
  expect(screen.getByRole("button", { name: "Sign out all sessions" })).toBeEnabled();
});
