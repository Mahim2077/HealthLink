"use client";

import { apiClientForPortal } from "@/lib/api/client";
import type { Portal } from "./types";

export async function refreshSession(portal: Portal): Promise<string> {
  return apiClientForPortal(portal).refreshSession();
}

export async function logout(portal: Portal): Promise<void> {
  await apiClientForPortal(portal).terminateSession("auth/logout");
}

export async function logoutAll(portal: Portal): Promise<void> {
  await apiClientForPortal(portal).terminateSession("auth/logout-all");
}

export async function replaceSession<T extends string | { access_token: string }>(
  issueSession: () => Promise<T>,
  portal: Portal,
): Promise<T> {
  return apiClientForPortal(portal).replaceSession(issueSession);
}
