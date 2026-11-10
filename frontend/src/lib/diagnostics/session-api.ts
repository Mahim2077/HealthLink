"use client";

import { apiClient } from "@/lib/api/client";

export type TestChoice = { code: string; name: string; aliases: string[] };
export type SessionStep = "CHECKED_IN" | "COLLECTED" | "PERFORMED";
export type SessionStatus = SessionStep | "REQUESTED" | "ACCEPTED" | "PUBLISHED" | "EXPIRED" | "CANCELLED" | "UNABLE";
export const closureReasons = {
  EQUIPMENT: "Lab equipment unavailable",
  STAFF: "Staff unavailable",
  SPECIMEN: "Sample could not be processed",
  OTHER: "Other lab issue",
} as const;
export type ClosureReason = keyof typeof closureReasons;
export type LabSession = {
  id: string;
  catalog_code: string;
  test_name: string;
  status: SessionStatus;
  created_at: string;
  attendance_deadline: string | null;
  facility_name: string | null;
  closed_reason: ClosureReason | null;
  share_code: string | null;
  patient_name: string | null;
  report_version: number | null;
  report_test_name: string | null;
  draft_version: number | null;
  draft_test_name: string | null;
  draft_tested_at: string | null;
};

const citizenPath = "citizens/me/diagnostic-sessions";
const labPath = "professionals/me/diagnostic-sessions";

export const getTestCatalog = () => apiClient.get<TestChoice[]>("diagnostics/test-catalog");
export const getLabSessions = (lab: boolean, page: number) => apiClient.get<LabSession[]>(`${lab ? labPath : citizenPath}?page=${page}`, { cache: "no-store" });
export const startLabSession = (id: string, catalog_code: string) => apiClient.post<LabSession, { id: string; catalog_code: string }>(citizenPath, { id, catalog_code });
export const cancelLabSession = (id: string) => apiClient.post<LabSession>(`${citizenPath}/${id}/cancel`);
export const acceptLabSession = (code: string, attendance_deadline: string) => apiClient.post<LabSession, { code: string; attendance_deadline: string }>(`${labPath}/accept`, { code, attendance_deadline });
export const advanceLabSession = (id: string, step: SessionStep, tested_at?: string) =>
  apiClient.post<LabSession, { tested_at: string }>(`${labPath}/${id}/steps/${step}`, tested_at ? { tested_at } : undefined);
export const closeLabSession = (id: string, reason: ClosureReason) => apiClient.post<LabSession, { reason: ClosureReason }>(`${labPath}/${id}/close`, { reason });
export const stageLabPdf = (id: string, file: File, catalogCode?: string, testedAt?: string) => {
  const params = new URLSearchParams();
  if (catalogCode) params.set("catalog_code", catalogCode);
  if (testedAt) params.set("tested_at", testedAt);
  return apiClient.request<LabSession>(`${labPath}/${id}/pdf?${params}`, {
    method: "PUT", body: file, headers: { "Content-Type": "application/pdf" },
  });
};
export const publishLabPdf = (id: string, version: number) => apiClient.post<LabSession, { version: number }>(`${labPath}/${id}/publish`, { version });
export const withdrawLabPdf = (id: string, version: number) => apiClient.post<LabSession, { version: number }>(`${labPath}/${id}/withdraw`, { version });
export const readDiagnosticPdf = (id: string, draftVersion?: number, signal?: AbortSignal) => apiClient.getBlob(
  draftVersion === undefined ? `diagnostic-sessions/${id}/pdf` : `${labPath}/${id}/pdf/${draftVersion}`,
  { signal, cache: "no-store" },
);
