import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), replaceSession: vi.fn() }));

vi.mock("@/lib/api/client", () => ({ apiClient: { get: mocks.get, post: mocks.post } }));
vi.mock("@/lib/auth/actions", () => ({ replaceSession: mocks.replaceSession }));

import { loadProfessionalMe, loginProfessional, onboardProfessional, registerProfessional } from "./api";

describe("Professional API", () => {
  beforeEach(() => { mocks.get.mockReset(); mocks.post.mockReset(); mocks.replaceSession.mockReset(); });

  it("registers a new professional without attaching or refreshing auth", async () => {
    const request = {
      additional_info: "Experienced physician",
      bmdc_registration_number: "BMDC-1",
      designation: "Consultant",
      email: "doctor@example.com",
      facility_name: "Medical College Hospital",
      first_name: "Amina",
      last_name: "Rahman",
      nid_number: "NID-1",
      password: "StrongPassword123!",
      role_code: "DOCTOR" as const,
    };
    mocks.post.mockResolvedValue({ verification_status: "PENDING" });

    await registerProfessional(request);

    expect(mocks.post).toHaveBeenCalledWith(
      "auth/professional/register",
      request,
      { auth: false, retryOnUnauthorized: false },
    );
  });

  it("onboards an authenticated existing account without identity fields", async () => {
    const request = {
      additional_info: "Laboratory professional",
      designation: "Technologist",
      facility_name: "Diagnostic Centre",
      role_code: "LAB_TECHNICIAN" as const,
    };
    mocks.post.mockResolvedValue({ verification_status: "PENDING" });

    await onboardProfessional(request);

    expect(mocks.post).toHaveBeenCalledWith("professionals/me/onboard", request);
    expect(request).not.toHaveProperty("nid_number");
    expect(request).not.toHaveProperty("user_id");
  });

  it("logs in through the shared replacement barrier and loads active context", async () => {
    const response = { access_token: "professional-token", expires_in: 1800, portal: "PROFESSIONAL", role_code: "DOCTOR", role_registration_id: "r1", token_type: "bearer", verification_status: "VERIFIED" } as const;
    mocks.post.mockResolvedValue(response); mocks.replaceSession.mockImplementation(async (issue: () => Promise<string>) => issue());
    const request = { nid_number: "NID-1", password: "secret", role_code: "DOCTOR" as const };
    await expect(loginProfessional(request)).resolves.toEqual(response);
    expect(mocks.post).toHaveBeenCalledWith("auth/professional/login", request, { auth: false, retryOnUnauthorized: false });
    expect(mocks.replaceSession).toHaveBeenCalledOnce();
    mocks.get.mockResolvedValue({ role_code: "DOCTOR" }); await loadProfessionalMe();
    expect(mocks.get).toHaveBeenCalledWith("professionals/me");
  });
});
