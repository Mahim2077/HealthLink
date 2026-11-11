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

export async function replaceSession<T extends string | { access_token: string }>(
  issueSession: () => Promise<T>,
): Promise<T> {
  return apiClient.replaceSession(issueSession);
}
