"use client";
import { apiClient } from "@/lib/api/client";

export type LabItem = {
  parameter_name: string; result_value_text: string; result_value_numeric: string | null;
  unit: string | null; reference_range: string | null; flag: string | null;
};
export type LabDraft = { report_date: string; summary: string | null; items: LabItem[] };
export type LabReport = LabDraft & {
  id: string; diagnostic_test_id: string; citizen_id: string; status: "DRAFT" | "FINALIZED";
  finalized_at: string | null; test_name: string; facility_name: string | null;
};
export type LabTrendPoint = { report_id: string; report_date: string; parameter_name: string; value: string; unit: string | null };
export const readLabReport = (id: string) => apiClient.get<LabReport | null>(`diagnostic-tests/${encodeURIComponent(id)}/lab-report`);
export const saveLabReport = (id: string, body: LabDraft) => apiClient.put<LabReport, LabDraft>(`diagnostic-tests/${encodeURIComponent(id)}/lab-report`, body);
export const finalizeLabReport = (id: string) => apiClient.post<LabReport>(`diagnostic-tests/${encodeURIComponent(id)}/lab-report/finalize`);
export const listLabReports = (page: number) => apiClient.get<LabReport[]>(`citizens/me/lab-reports?page=${page}`);
export const listLabTrends = (page: number) => apiClient.get<LabTrendPoint[]>(`citizens/me/lab-trends?page=${page}`);
