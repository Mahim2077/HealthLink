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

export async function confirmFacilityLocation(id: string): Promise<Facility> {
  const response = await apiClient.post<
    { facility: Facility; message: string },
    Record<string, never>
  >(`admin/facilities/${id}/confirm-location`, {});
  return response.facility;
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
  specialization?: import("@/lib/doctors/specializations").DoctorSpecialization,
  qualification?: string,
): Promise<ProfessionalRegistrationDetail> {
  return apiClient.post<
    ProfessionalRegistrationDetail,
    { facility_id: string; specialization?: string; qualification?: string }
  >(
    `admin/professional-registrations/${id}/verify`,
    {
      facility_id: facilityId,
      ...(specialization ? { specialization } : {}),
      ...(qualification ? { qualification } : {}),
    },
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
  const payload: CitizenIdentitySearchFilters = {};
  if (filters.nid_number && filters.nid_number.trim()) {
    payload.nid_number = filters.nid_number.trim();
  }
  if (filters.birth_certificate_number && filters.birth_certificate_number.trim()) {
    payload.birth_certificate_number = filters.birth_certificate_number.trim();
  }
  if (filters.email && filters.email.trim()) {
    payload.email = filters.email.trim();
  }
  if (filters.user_id && filters.user_id.trim()) {
    payload.user_id = filters.user_id.trim();
  }
  if (filters.limit) {
    payload.limit = filters.limit;
  }
  // Identity filters belong in the body, not browser URLs or access logs.
  return apiClient.post<CitizenIdentitySummary[], CitizenIdentitySearchFilters>(
    "admin/citizen-identities/search", payload,
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
