"use client";

import { apiClient } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import { replaceSession } from "@/lib/auth/actions";

import type {
  AdminLoginRequest,
  AdminLoginResponse,
  AdminMe,
  CitizenIdentityCorrectionRequest,
  CitizenIdentityCorrectionResponse,
  CitizenIdentityDetail,
  CitizenIdentitySummary,
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

export type CitizenIdentitySearchFilters = {
  nid_number?: string;
  birth_certificate_number?: string;
  email?: string;
  user_id?: string;
  limit?: number;
};

export async function searchCitizenIdentities(
  filters: CitizenIdentitySearchFilters,
): Promise<CitizenIdentitySummary[]> {
  const params = new URLSearchParams();
  if (filters.nid_number && filters.nid_number.trim()) {
    params.set("nid_number", filters.nid_number.trim());
  }
  if (filters.birth_certificate_number && filters.birth_certificate_number.trim()) {
    params.set("birth_certificate_number", filters.birth_certificate_number.trim());
  }
  if (filters.email && filters.email.trim()) {
    params.set("email", filters.email.trim());
  }
  if (filters.user_id && filters.user_id.trim()) {
    params.set("user_id", filters.user_id.trim());
  }
  if (filters.limit) {
    params.set("limit", String(filters.limit));
  }
  const query = params.toString();
  return apiClient.get<CitizenIdentitySummary[]>(
    `admin/citizen-identities/search${query ? `?${query}` : ""}`,
  );
}

export async function loadCitizenIdentity(userId: string): Promise<CitizenIdentityDetail> {
  return apiClient.get<CitizenIdentityDetail>(`admin/citizen-identities/${userId}`);
}

export async function correctCitizenIdentity(
  userId: string,
  payload: CitizenIdentityCorrectionRequest,
): Promise<CitizenIdentityCorrectionResponse> {
  return apiClient.post<CitizenIdentityCorrectionResponse, CitizenIdentityCorrectionRequest>(
    `admin/citizen-identities/${userId}/correct`,
    payload,
  );
}
