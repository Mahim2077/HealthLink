"use client";

import { apiClient } from "@/lib/api/client";

export async function refreshSession(): Promise<string> {
  return apiClient.refreshSession();
}

export async function logout(): Promise<void> {
  await apiClient.terminateSession("auth/logout");
}

export async function logoutAll(): Promise<void> {
  await apiClient.terminateSession("auth/logout-all");
}

export async function replaceSession(
  issueSession: () => Promise<string>,
): Promise<string> {
  return apiClient.replaceSession(issueSession);
}
