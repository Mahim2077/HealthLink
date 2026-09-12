"use client";
import { apiClient } from "@/lib/api/client";
import type { DiagnosticStatus, DiagnosticTest, DiagnosticTestList, TechnicianChoice } from "./types";

export const listCitizenDiagnostics = () => apiClient.get<DiagnosticTestList>("citizens/me/diagnostic-tests");
export const listProfessionalDiagnostics = () => apiClient.get<DiagnosticTestList>("professionals/me/diagnostic-tests");
export const listDiagnosticTechnicians = (search = "", context?: { test_id?: string; visit_id?: string }) => {
  const params = new URLSearchParams({ search });
  if (context?.test_id) params.set("test_id", context.test_id);
  if (context?.visit_id) params.set("visit_id", context.visit_id);
  return apiClient.get<TechnicianChoice[]>(`professionals/diagnostic-technicians?${params}`);
};
export const createDiagnosticTest = (payload: { visit_id: string; test_name: string; instructions?: string | null; assigned_to_role_registration_id?: string | null }) => apiClient.post<DiagnosticTest, typeof payload>("professionals/current-patient/diagnostic-tests", payload);
export const assignDiagnosticTest = (id: string, assignee: string | null) => apiClient.put<DiagnosticTest, { assigned_to_role_registration_id: string | null }>(`professionals/me/diagnostic-tests/${id}/assignment`, { assigned_to_role_registration_id: assignee });
export const transitionDiagnosticTest = (id: string, status: DiagnosticStatus) => apiClient.post<DiagnosticTest>(`professionals/me/diagnostic-tests/${id}/transitions/${status}`);
