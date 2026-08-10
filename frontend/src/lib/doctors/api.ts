"use client";

import { apiClient } from "@/lib/api/client";

import type {
  DoctorProfile,
  DoctorSearchFilters,
  DoctorSummary,
  FacilityChoice,
  PracticeScheduleCreateResponse,
  PracticeScheduleDeleteResponse,
  PracticeScheduleEntry,
  PracticeScheduleWriteRequest,
} from "./types";

export async function searchDoctors(
  filters: DoctorSearchFilters,
): Promise<DoctorSummary[]> {
  const params = new URLSearchParams();
  if (filters.name && filters.name.trim()) {
    params.set("name", filters.name.trim());
  }
  if (filters.facility_name && filters.facility_name.trim()) {
    params.set("facility_name", filters.facility_name.trim());
  }
  if (filters.weekday) {
    params.set("weekday", filters.weekday);
  }
  if (filters.limit && filters.limit > 0) {
    params.set("limit", String(filters.limit));
  }
  const query = params.toString();
  return apiClient.get<DoctorSummary[]>(
    `doctors${query ? `?${query}` : ""}`,
  );
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