import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), replaceSession: vi.fn() }));
vi.mock("@/lib/api/client", () => ({ apiClient: { get: mocks.get, post: mocks.post } }));
vi.mock("@/lib/auth/actions", () => ({ replaceSession: mocks.replaceSession }));

import { loadAdminMe, loginAdmin } from "./api";

describe("Admin API", () => {
  beforeEach(() => { mocks.get.mockReset(); mocks.post.mockReset(); mocks.replaceSession.mockReset(); });

  it("serializes admin login through the shared session replacement barrier", async () => {
    const response = { access_token: "admin-token", expires_in: 1800, portal: "ADMIN" as const, token_type: "bearer" as const };
    mocks.post.mockResolvedValue(response);
    mocks.replaceSession.mockImplementation(async (issue: () => Promise<string>) => issue());
    await expect(loginAdmin({ email: "admin@example.com", password: "secret" })).resolves.toEqual(response);
    expect(mocks.post).toHaveBeenCalledWith("auth/admin/login", { email: "admin@example.com", password: "secret" }, { auth: false, retryOnUnauthorized: false });
    expect(mocks.replaceSession).toHaveBeenCalledOnce();
  });

  it("rejects a non-admin login response", async () => {
    mocks.post.mockResolvedValue({ access_token: "wrong", expires_in: 1800, portal: "CITIZEN", token_type: "bearer" });
    mocks.replaceSession.mockImplementation(async (issue: () => Promise<string>) => issue());
    await expect(loginAdmin({ email: "admin@example.com", password: "secret" })).rejects.toMatchObject({ status: 403 });
  });

  it("loads the current admin through the protected endpoint", async () => {
    mocks.get.mockResolvedValue({ email: "admin@example.com" });
    await loadAdminMe();
    expect(mocks.get).toHaveBeenCalledWith("admin/me");
  });
});
