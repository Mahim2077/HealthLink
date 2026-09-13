"use client";
import { apiClient } from "@/lib/api/client";

export const scopes = {
  FULL_MEDICAL_HISTORY: "Full medical history",
  VISITS_ONLY: "Visits only",
  PRESCRIPTIONS_ONLY: "Prescriptions only",
  LAB_REPORTS_ONLY: "Lab reports only",
  EMERGENCY_PROFILE_ONLY: "Emergency profile only",
} as const;
export type Scope = keyof typeof scopes;
export type Grant = { id: string; professional_name: string; designation: string | null; access_scope: Scope; expires_at: string | null; revoked_at: string | null; active: boolean };
export type Doctor = { id: string; name: string; designation: string | null; facility_name: string | null };
export type GrantedPatient = { id: string; citizen_id: string; citizen_name: string; access_scope: Scope; expires_at: string | null };
export type Page<T> = { grants: T[]; page: number; has_next: boolean };
export const listGrants = (page = 1) => apiClient.get<Page<Grant>>(`citizens/me/access-grants?page=${page}`);
export const findDoctors = (search: string) => apiClient.get<Doctor[]>(`citizens/me/access-grant-professionals?${new URLSearchParams({ search })}`);
export const createGrant = (payload: { professional_role_registration_id: string; access_scope: Scope; expires_at: string | null }) => apiClient.post<Grant, typeof payload>("citizens/me/access-grants", payload);
export const revokeGrant = (id: string) => apiClient.post<Grant>(`citizens/me/access-grants/${id}/revoke`);
export const grantedPatients = (page = 1) => apiClient.get<Page<GrantedPatient>>(`professionals/me/access-grants?page=${page}`);
export type SharedRecord = { id: string; resource_type: string; title: string; occurred_at: string; summary: string | null; detail_url: string | null };
export const sharedRecords = (citizenId: string, type: string, page: number) => apiClient.get<{ records: SharedRecord[]; has_next: boolean }>(`professionals/patients/${citizenId}/medical-history?${new URLSearchParams({ ...(type ? { record_type: type } : {}), page: String(page) })}`);
