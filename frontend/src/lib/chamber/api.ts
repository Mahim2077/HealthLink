"use client";

import { apiClient } from "@/lib/api/client";

import type {
  ChamberQueueActionResponse,
  ChamberSessionFinishResponse,
  ChamberSessionStartRequest,
  ChamberSessionView,
} from "./types";

// All chamber routes live under the verified-doctor guard so a plain
// fetch from the citizen or admin portal would 403; the apiClient
// still adds the bearer token.

function buildQuery(
  facility_id: string,
  session_date: string | null,
): string {
  const params = new URLSearchParams();
  params.set("facility_id", facility_id);
  if (session_date) params.set("session_date", session_date);
  return params.toString();
}

export async function loadChamberSession(
  facility_id: string,
  session_date: string | null,
): Promise<ChamberSessionView | null> {
  return apiClient.get<ChamberSessionView | null>(
    `professionals/chamber/sessions/today?${buildQuery(facility_id, session_date)}`,
  );
}

export async function startChamberSession(
  payload: ChamberSessionStartRequest,
): Promise<ChamberSessionView> {
  return apiClient.post<ChamberSessionView, ChamberSessionStartRequest>(
    "professionals/chamber/sessions/start",
    payload,
  );
}

export async function finishChamberSession(
  facility_id: string,
  session_date: string | null,
): Promise<ChamberSessionFinishResponse> {
  return apiClient.post<ChamberSessionFinishResponse, Record<string, never>>(
    `professionals/chamber/sessions/finish?${buildQuery(facility_id, session_date)}`,
    {},
  );
}

export async function callNextPatient(
  facility_id: string,
  session_date: string | null,
): Promise<ChamberQueueActionResponse> {
  return apiClient.post<ChamberQueueActionResponse, Record<string, never>>(
    `professionals/chamber/queue/call-next?${buildQuery(facility_id, session_date)}`,
    {},
  );
}

export async function actOnCurrentPatient(
  queue_id: string,
  action: "skip" | "no-show",
): Promise<ChamberQueueActionResponse> {
  return apiClient.post<ChamberQueueActionResponse, Record<string, never>>(
    `professionals/chamber/queue/${queue_id}/${action}`,
    {},
  );
}

export async function removeQueueEntry(
  queue_id: string,
): Promise<ChamberQueueActionResponse> {
  return apiClient.post<ChamberQueueActionResponse, Record<string, never>>(
    `professionals/chamber/queue/${queue_id}/remove`,
    {},
  );
}
