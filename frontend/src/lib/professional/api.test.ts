import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ post: vi.fn() }));

vi.mock("@/lib/api/client", () => ({ apiClient: { post: mocks.post } }));

import { onboardProfessional, registerProfessional } from "./api";

describe("Professional API", () => {
  beforeEach(() => mocks.post.mockReset());

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
});
