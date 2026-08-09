import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  replaceSession: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    get: apiMocks.get,
    post: apiMocks.post,
    put: apiMocks.put,
  },
}));

vi.mock("@/lib/auth/actions", () => ({
  replaceSession: apiMocks.replaceSession,
}));

import {
  addCitizenNid,
  loadCitizenDashboard,
  loginCitizen,
  registerCitizen,
  updateCitizenProfile,
} from "./api";

describe("Citizen API", () => {
  beforeEach(() => {
    apiMocks.get.mockReset();
    apiMocks.post.mockReset();
    apiMocks.put.mockReset();
    apiMocks.replaceSession.mockReset();
  });

  it("registers without creating an authenticated session", async () => {
    const request = {
      date_of_birth: "1990-01-02",
      email: "citizen@example.com",
      first_name: "Amina",
      gender: "FEMALE",
      last_name: "Rahman",
      nid_number: "00123-AB",
      password: "secure-pass",
    };
    const response = {
      citizen_id: "citizen-1",
      created_at: "2026-08-10T00:00:00Z",
      email: request.email,
      first_name: request.first_name,
      last_name: request.last_name,
      registered_with: "NID" as const,
      user_id: "user-1",
    };
    apiMocks.post.mockResolvedValue(response);

    await expect(registerCitizen(request)).resolves.toEqual(response);
    expect(apiMocks.post).toHaveBeenCalledWith(
      "auth/citizen/register",
      request,
      { auth: false, retryOnUnauthorized: false },
    );
    expect(apiMocks.replaceSession).not.toHaveBeenCalled();
  });

  it("serializes citizen login through session replacement", async () => {
    const response = {
      access_token: "citizen-token",
      expires_in: 1800,
      portal: "CITIZEN" as const,
      token_type: "bearer" as const,
    };
    apiMocks.post.mockResolvedValue(response);
    apiMocks.replaceSession.mockImplementation(
      async (issueSession: () => Promise<string>) => issueSession(),
    );

    await expect(
      loginCitizen({ email: "citizen@example.com", password: "secret" }),
    ).resolves.toEqual(response);
    expect(apiMocks.replaceSession).toHaveBeenCalledOnce();
    expect(apiMocks.post).toHaveBeenCalledWith(
      "auth/citizen/login",
      { email: "citizen@example.com", password: "secret" },
      { auth: false, retryOnUnauthorized: false },
    );
  });

  it("rejects a login response for a different portal", async () => {
    apiMocks.post.mockResolvedValue({
      access_token: "professional-token",
      expires_in: 1800,
      portal: "PROFESSIONAL",
      token_type: "bearer",
    });
    apiMocks.replaceSession.mockImplementation(
      async (issueSession: () => Promise<string>) => issueSession(),
    );

    await expect(
      loginCitizen({ email: "citizen@example.com", password: "secret" }),
    ).rejects.toMatchObject({ status: 403 });
  });

  it("loads the citizen profile and identity together", async () => {
    const profile = { citizen_id: "citizen-1", first_name: "Amina" };
    const identity = { registered_with: "BCN" };
    apiMocks.get
      .mockResolvedValueOnce(profile)
      .mockResolvedValueOnce(identity);

    await expect(loadCitizenDashboard()).resolves.toEqual({
      identity,
      profile,
    });
    expect(apiMocks.get).toHaveBeenNthCalledWith(1, "citizens/me");
    expect(apiMocks.get).toHaveBeenNthCalledWith(
      2,
      "citizens/me/identity",
    );
  });

  it("updates only the documented editable profile fields", async () => {
    const request = {
      address: "Chattogram",
      blood_group: "B+",
      date_of_birth: "1990-01-02",
      first_name: "Ayesha",
      gender: "FEMALE",
      last_name: "Karim",
    };
    apiMocks.put.mockResolvedValue({ ...request, email: "citizen@example.com" });

    await updateCitizenProfile(request);

    expect(apiMocks.put).toHaveBeenCalledWith("citizens/me/profile", request);
    expect(request).not.toHaveProperty("nid_number");
    expect(request).not.toHaveProperty("birth_certificate_number");
  });

  it("uses the dedicated one-time NID endpoint with explicit confirmation", async () => {
    const request = { confirmation: "CONFIRM", nid_number: "NID-001" };
    apiMocks.post.mockResolvedValue({
      birth_certificate_number: "BCN-001",
      nid_added_at: "2026-08-10T00:00:00Z",
      nid_number: "NID-001",
      registered_with: "BCN",
    });

    await addCitizenNid(request);

    expect(apiMocks.post).toHaveBeenCalledWith(
      "citizens/me/identity/add-nid",
      request,
    );
  });
});
