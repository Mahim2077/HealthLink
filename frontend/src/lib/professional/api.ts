"use client";

import { apiClient } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import { replaceSession } from "@/lib/auth/actions";
import type { AccessTokenResponse } from "@/lib/auth/types";

import type {
  CitizenProfileSetup,
  ProfessionalApplicationResponse,
  ProfessionalOnboardingRequest,
  ProfessionalRegistrationRequest,
  ProfessionalLoginRequest,
  ProfessionalLoginResponse,
  ProfessionalMe,
} from "./types";

export async function registerProfessional(
  request: ProfessionalRegistrationRequest,
): Promise<ProfessionalApplicationResponse> {
  return replaceSession(() => apiClient.post<
    ProfessionalApplicationResponse & AccessTokenResponse,
    ProfessionalRegistrationRequest
  >("auth/professional/register", request, {
    auth: false,
    portal: "PROFESSIONAL",
    retryOnUnauthorized: false,
  }), "PROFESSIONAL");
}

export async function onboardProfessional(
  request: ProfessionalOnboardingRequest,
): Promise<ProfessionalApplicationResponse> {
  return apiClient.post<
    ProfessionalApplicationResponse,
    ProfessionalOnboardingRequest
  >("professionals/me/onboard", request, { portal: "CITIZEN" });
}

export async function loginProfessional(
  request: ProfessionalLoginRequest,
): Promise<ProfessionalLoginResponse> {
  let response: ProfessionalLoginResponse | null = null;
  await replaceSession(async () => {
    response = await apiClient.post<ProfessionalLoginResponse, ProfessionalLoginRequest>(
      "auth/professional/login", request,
      { auth: false, portal: "PROFESSIONAL", retryOnUnauthorized: false },
    );
    if (response.portal !== "PROFESSIONAL") {
      throw new ApiError(403, "This session does not belong to the Professional Portal.", response);
    }
    return response.access_token;
  }, "PROFESSIONAL");
  if (response === null) throw new ApiError(500, "Professional login did not return a session.");
  return response;
}

export async function loadProfessionalMe(): Promise<ProfessionalMe> {
  return apiClient.get<ProfessionalMe>("professionals/me");
}

export function setupProfessionalCitizenProfile(payload: CitizenProfileSetup): Promise<void> {
  return apiClient.put<void, CitizenProfileSetup>("professionals/me/citizen-profile", payload);
}
