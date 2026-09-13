import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { AccessHistoryPage } from "./access-history";

const mocks = vi.hoisted(() => ({ get: vi.fn(), auth: vi.fn() }));
vi.mock("@/lib/api/client", () => ({ apiClient: { get: mocks.get } }));
vi.mock("@/components/auth/auth-provider", () => ({ usePortalAuth: mocks.auth }));
beforeEach(() => {
  vi.clearAllMocks();
  mocks.auth.mockReturnValue({ status: "authenticated", isRequiredPortal: true, claims: { sid: "owner" } });
});
it("shows metadata and paginates without keeping old records", async () => {
  mocks.get.mockResolvedValueOnce({ page: 1, has_next: true, items: [{ id: "one", actor_name: "Dr. Test", role: "Doctor", facility: "Test clinic", resource_type: "EMERGENCY_PROFILE", action: "READ", access_source: "GRANT", created_at: "2026-09-12T12:00:00Z" }] })
    .mockResolvedValueOnce({ page: 2, has_next: false, items: [] });
  render(<AccessHistoryPage />);
  expect(await screen.findByText("Dr. Test")).toBeInTheDocument();
  expect(screen.getByText("Access through grant")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Next" }));
  expect(await screen.findByText("No access activity")).toBeInTheDocument();
  expect(screen.queryByText("Dr. Test")).toBeNull();
  expect(mocks.get).toHaveBeenLastCalledWith("citizens/me/access-history?page=2");
});
it("retries failures", async () => {
  mocks.get.mockRejectedValueOnce(new Error("Offline")).mockResolvedValueOnce({ page: 1, has_next: false, items: [] });
  render(<AccessHistoryPage />);
  expect(await screen.findByText("Offline")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /try again/i }));
  expect(await screen.findByText("No access activity")).toBeInTheDocument();
});
it("does not fetch clinical activity for another portal", () => {
  mocks.auth.mockReturnValue({ status: "authenticated", isRequiredPortal: false });
  render(<AccessHistoryPage />);
  expect(mocks.get).not.toHaveBeenCalled();
});
