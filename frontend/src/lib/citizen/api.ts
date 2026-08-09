"use client";

import { apiClient } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import { replaceSession } from "@/lib/auth/actions";

import type {
  CitizenDashboardData,
  CitizenAddNidRequest,
  CitizenIdentity,
  CitizenLoginRequest,
  CitizenLoginResponse,
  CitizenProfile,
  CitizenProfileUpdateRequest,
  CitizenRegistrationRequest,
  CitizenRegistrationResponse,
} from "./types";

export async function registerCitizen(
  request: CitizenRegistrationRequest,
): Promise<CitizenRegistrationResponse> {
  return apiClient.post<
    CitizenRegistrationResponse,
    CitizenRegistrationRequest
  >("auth/citizen/register", request, {
    auth: false,
    retryOnUnauthorized: false,
  });
}

export async function loginCitizen(
  request: CitizenLoginRequest,
): Promise<CitizenLoginResponse> {
  let response: CitizenLoginResponse | null = null;

  await replaceSession(async () => {
    response = await apiClient.post<
      CitizenLoginResponse,
      CitizenLoginRequest
    >("auth/citizen/login", request, {
      auth: false,
      retryOnUnauthorized: false,
    });

    if (response.portal !== "CITIZEN") {
      throw new ApiError(
        403,
        "This session does not belong to the Citizen Portal.",
        response,
      );
    }

    return response.access_token;
  });

  if (response === null) {
    throw new ApiError(500, "Citizen login did not return a session.");
  }

  return response;
}

export async function loadCitizenDashboard(): Promise<CitizenDashboardData> {
  const [profile, identity] = await Promise.all([
    apiClient.get<CitizenProfile>("citizens/me"),
    apiClient.get<CitizenIdentity>("citizens/me/identity"),
  ]);

  return { identity, profile };
}

export async function updateCitizenProfile(
  request: CitizenProfileUpdateRequest,
): Promise<CitizenProfile> {
  return apiClient.put<CitizenProfile, CitizenProfileUpdateRequest>(
    "citizens/me/profile",
    request,
  );
}

export async function addCitizenNid(
  request: CitizenAddNidRequest,
): Promise<CitizenIdentity> {
  return apiClient.post<CitizenIdentity, CitizenAddNidRequest>(
    "citizens/me/identity/add-nid",
    request,
  );
}
