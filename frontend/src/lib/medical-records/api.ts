"use client";

import { apiClient } from "@/lib/api/client";

import type {
  MedicalHistoryLoadAction,
  MedicalHistoryPage,
  MedicalHistoryQuery,
} from "./types";

function historyPath(path: string, query: MedicalHistoryQuery = {}): string {
  const params = new URLSearchParams();
  if (query.resource_type) params.set("resource_type", query.resource_type);
  if (query.date_from) params.set("date_from", query.date_from);
  if (query.date_to) params.set("date_to", query.date_to);
  if (query.page !== undefined) params.set("page", String(query.page));
  if (query.page_size !== undefined) {
    params.set("page_size", String(query.page_size));
  }
  const serialized = params.toString();
  return serialized ? `${path}?${serialized}` : path;
}

export const listCitizenMedicalHistory: MedicalHistoryLoadAction = async (
  query = {},
): Promise<MedicalHistoryPage> =>
  apiClient.get<MedicalHistoryPage>(
    historyPath("citizens/me/medical-history", query),
  );

export const listCurrentPatientMedicalHistory: MedicalHistoryLoadAction = async (
  query = {},
): Promise<MedicalHistoryPage> =>
  apiClient.get<MedicalHistoryPage>(
    historyPath("professionals/current-patient/medical-history", query),
  );
