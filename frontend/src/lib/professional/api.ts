"use client";

import { apiClient } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import { replaceSession } from "@/lib/auth/actions";

import type {
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
  return apiClient.post<
    ProfessionalApplicationResponse,
    ProfessionalRegistrationRequest
  >("auth/professional/register", request, {
    auth: false,
    retryOnUnauthorized: false,
  });
}

export async function onboardProfessional(
  request: ProfessionalOnboardingRequest,
): Promise<ProfessionalApplicationResponse> {
  return apiClient.post<
    ProfessionalApplicationResponse,
    ProfessionalOnboardingRequest
  >("professionals/me/onboard", request);
}

export async function loginProfessional(
  request: ProfessionalLoginRequest,
): Promise<ProfessionalLoginResponse> {
  let response: ProfessionalLoginResponse | null = null;
  await replaceSession(async () => {
    response = await apiClient.post<ProfessionalLoginResponse, ProfessionalLoginRequest>(
      "auth/professional/login", request, { auth: false, retryOnUnauthorized: false },
    );
    if (response.portal !== "PROFESSIONAL") {
      throw new ApiError(403, "This session does not belong to the Professional Portal.", response);
    }
    return response.access_token;
  });
  if (response === null) throw new ApiError(500, "Professional login did not return a session.");
  return response;
}

export async function loadProfessionalMe(): Promise<ProfessionalMe> {
  return apiClient.get<ProfessionalMe>("professionals/me");
}
