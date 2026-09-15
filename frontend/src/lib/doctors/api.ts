"use client";

import { apiClient } from "@/lib/api/client";

import type {
  DoctorProfile,
  DoctorDiscoveryFacility,
  DoctorSearchFilters,
  DoctorSearchResponse,
  FacilityChoice,
  PracticeScheduleCreateResponse,
  PracticeScheduleDeleteResponse,
  PracticeScheduleEntry,
  PracticeScheduleWriteRequest,
} from "./types";

export async function searchDoctors(
  filters: DoctorSearchFilters,
): Promise<DoctorSearchResponse> {
  const payload: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(filters)) {
    if (value === undefined || value === "") continue;
    if (typeof value === "string") {
      const trimmed = value.trim();
      if (trimmed) payload[key] = trimmed;
    } else {
      payload[key] = value;
    }
  }
  return apiClient.post<DoctorSearchResponse, DoctorSearchFilters>(
    "doctors/search",
    payload as DoctorSearchFilters,
  );
}

export async function loadDoctorDiscoveryFacilities(): Promise<DoctorDiscoveryFacility[]> {
  return apiClient.get<DoctorDiscoveryFacility[]>("doctors/facilities");
}

export async function loadDoctorProfile(
  doctorUserId: string,
): Promise<DoctorProfile> {
  return apiClient.get<DoctorProfile>(`doctors/${doctorUserId}`);
}

export async function loadPracticeSchedule(): Promise<PracticeScheduleEntry[]> {
  return apiClient.get<PracticeScheduleEntry[]>(
    "professionals/me/practice-schedule",
  );
}

export async function createPracticeSchedule(
  payload: PracticeScheduleWriteRequest,
): Promise<PracticeScheduleCreateResponse> {
  return apiClient.post<PracticeScheduleCreateResponse, PracticeScheduleWriteRequest>(
    "professionals/me/practice-schedule",
    payload,
  );
}

export async function updatePracticeSchedule(
  scheduleId: string,
  payload: PracticeScheduleWriteRequest,
): Promise<PracticeScheduleEntry> {
  return apiClient.put<PracticeScheduleEntry, PracticeScheduleWriteRequest>(
    `professionals/me/practice-schedule/${scheduleId}`,
    payload,
  );
}

export async function deletePracticeSchedule(
  scheduleId: string,
): Promise<PracticeScheduleDeleteResponse> {
  return apiClient.delete<PracticeScheduleDeleteResponse>(
    `professionals/me/practice-schedule/${scheduleId}`,
  );
}

export async function loadEligibleFacilities(): Promise<FacilityChoice[]> {
  return apiClient.get<FacilityChoice[]>("professionals/me/eligible-facilities");
}
