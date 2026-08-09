"use client";

import { apiClient } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import { replaceSession } from "@/lib/auth/actions";

import type { AdminLoginRequest, AdminLoginResponse, AdminMe } from "./types";

export async function loginAdmin(request: AdminLoginRequest): Promise<AdminLoginResponse> {
  let response: AdminLoginResponse | null = null;
  await replaceSession(async () => {
    response = await apiClient.post<AdminLoginResponse, AdminLoginRequest>(
      "auth/admin/login",
      request,
      { auth: false, retryOnUnauthorized: false },
    );
    if (response.portal !== "ADMIN") {
      throw new ApiError(403, "This session does not belong to the Admin Portal.", response);
    }
    return response.access_token;
  });
  if (response === null) throw new ApiError(500, "Admin login did not return a session.");
  return response;
}

export async function loadAdminMe(): Promise<AdminMe> {
  return apiClient.get<AdminMe>("admin/me");
}
