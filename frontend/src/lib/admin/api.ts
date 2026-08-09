"use client";

import { apiClient } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import { replaceSession } from "@/lib/auth/actions";

import type {
  AdminLoginRequest,
  AdminLoginResponse,
  AdminMe,
  Facility,
  FacilityWriteRequest,
  ProfessionalRegistrationDetail,
  ProfessionalRegistrationSummary,
  VerificationStatus,
} from "./types";

export async function loginAdmin(request: AdminLoginRequest): Promise<AdminLoginResponse> {
  let response: AdminLoginResponse | null = null;
  await replaceSession(async () => {
    response = await apiClient.post<AdminLoginResponse, AdminLoginRequest>(
      "auth/admin/login",
      request,
      { auth: false, retryOnUnauthorized: false },
    );
    if (response.portal !== "ADMIN") {
      throw new ApiError(403, "This session does not belong to the Admin Portal.", response);
    }
    return response.access_token;
  });
  if (response === null) throw new ApiError(500, "Admin login did not return a session.");
  return response;
}

export async function loadAdminMe(): Promise<AdminMe> {
  return apiClient.get<AdminMe>("admin/me");
}

export async function loadFacilities(): Promise<Facility[]> {
  return apiClient.get<Facility[]>("admin/facilities");
}

export async function createFacility(payload: FacilityWriteRequest): Promise<Facility> {
  return apiClient.post<Facility, FacilityWriteRequest>("admin/facilities", payload);
}

export async function updateFacility(id: string, payload: FacilityWriteRequest): Promise<Facility> {
  return apiClient.put<Facility, FacilityWriteRequest>(`admin/facilities/${id}`, payload);
}

export async function loadProfessionalRegistrations(
  verificationStatus?: VerificationStatus,
): Promise<ProfessionalRegistrationSummary[]> {
  const query = verificationStatus
    ? `?verification_status=${encodeURIComponent(verificationStatus)}`
    : "";
  return apiClient.get<ProfessionalRegistrationSummary[]>(
    `admin/professional-registrations${query}`,
  );
}

export async function loadProfessionalRegistration(
  id: string,
): Promise<ProfessionalRegistrationDetail> {
  return apiClient.get<ProfessionalRegistrationDetail>(
    `admin/professional-registrations/${id}`,
  );
}

export async function verifyProfessionalRegistration(
  id: string,
  facilityId: string,
): Promise<ProfessionalRegistrationDetail> {
  return apiClient.post<ProfessionalRegistrationDetail, { facility_id: string }>(
    `admin/professional-registrations/${id}/verify`,
    { facility_id: facilityId },
  );
}

export async function rejectProfessionalRegistration(
  id: string,
  reason: string,
): Promise<ProfessionalRegistrationDetail> {
  return apiClient.post<ProfessionalRegistrationDetail, { reason: string }>(
    `admin/professional-registrations/${id}/reject`,
    { reason },
  );
}
