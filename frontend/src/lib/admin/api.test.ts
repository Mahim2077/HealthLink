import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), replaceSession: vi.fn() }));
vi.mock("@/lib/api/client", () => ({ apiClient: { get: mocks.get, post: mocks.post, put: mocks.put } }));
vi.mock("@/lib/auth/actions", () => ({ replaceSession: mocks.replaceSession }));

import { createFacility, loadAdminMe, loadFacilities, loadProfessionalRegistration, loadProfessionalRegistrations, loginAdmin, rejectProfessionalRegistration, updateFacility, verifyProfessionalRegistration } from "./api";

describe("Admin API", () => {
  beforeEach(() => { mocks.get.mockReset(); mocks.post.mockReset(); mocks.put.mockReset(); mocks.replaceSession.mockReset(); });

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

  it("uses the documented facility CRUD endpoints", async () => {
    const payload = { address: "Dhaka", email: null, facility_type: "HOSPITAL" as const, is_active: true, name: "General", phone: null, registration_number: null };
    mocks.get.mockResolvedValue([]); mocks.post.mockResolvedValue({ id: "f1" }); mocks.put.mockResolvedValue({ id: "f1" });
    await loadFacilities(); await createFacility(payload); await updateFacility("f1", payload);
    expect(mocks.get).toHaveBeenCalledWith("admin/facilities");
    expect(mocks.post).toHaveBeenCalledWith("admin/facilities", payload);
    expect(mocks.put).toHaveBeenCalledWith("admin/facilities/f1", payload);
  });

  it("uses the documented verification queue, detail, verify, and reject endpoints", async () => {
    mocks.get.mockResolvedValue([]); mocks.post.mockResolvedValue({});
    await loadProfessionalRegistrations("PENDING");
    await loadProfessionalRegistration("r1");
    await verifyProfessionalRegistration("r1", "f1");
    await rejectProfessionalRegistration("r1", "Evidence mismatch");
    expect(mocks.get).toHaveBeenNthCalledWith(1, "admin/professional-registrations?verification_status=PENDING");
    expect(mocks.get).toHaveBeenNthCalledWith(2, "admin/professional-registrations/r1");
    expect(mocks.post).toHaveBeenNthCalledWith(1, "admin/professional-registrations/r1/verify", { facility_id: "f1" });
    expect(mocks.post).toHaveBeenNthCalledWith(2, "admin/professional-registrations/r1/reject", { reason: "Evidence mismatch" });
  });
});
