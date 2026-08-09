"use client";

import { apiClient } from "@/lib/api/client";

import type {
  ProfessionalApplicationResponse,
  ProfessionalOnboardingRequest,
  ProfessionalRegistrationRequest,
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
