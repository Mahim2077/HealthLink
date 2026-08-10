"use client";

import { apiClient } from "@/lib/api/client";

import type {
  CitizenVisitListResponse,
  DoctorCurrentPatientView,
  VisitDraftUpdateRequest,
  VisitDraftView,
} from "./types";

// All doctor endpoints live under the verified-doctor guard; the
// citizen endpoints live under the citizen-portal guard. Both add the
// bearer token via apiClient.

export async function loadCurrentPatient(): Promise<DoctorCurrentPatientView | null> {
  return apiClient.get<DoctorCurrentPatientView | null>(
    "doctors/me/visits/current-patient",
  );
}

export async function startVisitForCurrent(
  queue_id: string,
): Promise<VisitDraftView> {
  return apiClient.post<VisitDraftView, Record<string, never>>(
    `doctors/me/visits/start-for-current/${queue_id}`,
    {},
  );
}

export async function readDoctorVisit(visit_id: string): Promise<VisitDraftView> {
  return apiClient.get<VisitDraftView>(`doctors/me/visits/${visit_id}`);
}

export async function updateDoctorVisit(
  visit_id: string,
  payload: VisitDraftUpdateRequest,
): Promise<VisitDraftView> {
  return apiClient.put<VisitDraftView, VisitDraftUpdateRequest>(
    `doctors/me/visits/${visit_id}`,
    payload,
  );
}

export async function listCitizenVisitsToday(): Promise<CitizenVisitListResponse> {
  return apiClient.get<CitizenVisitListResponse>("citizens/me/visits/today");
}

export async function readCitizenVisit(visit_id: string): Promise<VisitDraftView> {
  return apiClient.get<VisitDraftView>(`citizens/me/visits/${visit_id}`);
}
