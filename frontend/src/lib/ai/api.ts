"use client";

import { apiClient } from "@/lib/api/client";

import type {
  AiChatResponse,
  ChatMode,
  ConversationDetail,
  ConversationPage,
  ConversationSendRequest,
  ConversationSendResponse,
  LabReportExplanation,
  MedicalHistorySummary,
  PrescriptionExplanation,
  SymptomGuidance,
} from "./types";

export const explainPrescription = (prescriptionId: string) =>
  apiClient.post<PrescriptionExplanation>(
    `ai/prescriptions/${encodeURIComponent(prescriptionId)}/explain`,
  );

export const explainLabReport = (reportId: string) =>
  apiClient.post<LabReportExplanation>(
    `ai/lab-reports/${encodeURIComponent(reportId)}/explain`,
  );

export const summarizeMedicalHistory = () =>
  apiClient.post<MedicalHistorySummary, { use_my_health_records: true }>(
    "ai/medical-history/summary",
    { use_my_health_records: true },
  );

export const askAi = (payload: {
  mode: ChatMode;
  message: string;
  use_my_health_records: boolean;
}) => apiClient.post<AiChatResponse, typeof payload>("ai/chat", payload);

export const requestSymptomGuidance = (symptoms: string) =>
  apiClient.post<SymptomGuidance, { symptoms: string }>(
    "ai/symptom-guidance",
    { symptoms },
  );

export const listConversations = (offset = 0, signal?: AbortSignal) =>
  apiClient.get<ConversationPage>(`ai/conversations?offset=${offset}`, { cache: "no-store", signal });
export const loadConversation = (id: string, signal?: AbortSignal) =>
  apiClient.get<ConversationDetail>(`ai/conversations/${encodeURIComponent(id)}`, { cache: "no-store", signal });
export const deleteConversation = (id: string) =>
  apiClient.delete<void>(`ai/conversations/${encodeURIComponent(id)}`);
export const sendConversationMessage = (payload: ConversationSendRequest, signal?: AbortSignal) =>
  apiClient.post<ConversationSendResponse, ConversationSendRequest>("ai/conversation-messages", payload, { signal });
