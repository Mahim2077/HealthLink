"use client";

import { buildApiUrl } from "@/lib/api/config";
import { ApiError } from "@/lib/api/errors";

import type { AccessTokenResponse, Portal } from "./types";

export const SESSION_PORTAL_HEADER = "X-HealthLink-Portal";

export async function requestAccessTokenRefresh(
  fetchImplementation: typeof fetch = fetch,
  portal?: Portal,
): Promise<string> {
  const response = await fetchImplementation(buildApiUrl("auth/refresh"), {
    method: "POST",
    credentials: "include",
    headers: {
      Accept: "application/json",
      ...(portal && { [SESSION_PORTAL_HEADER]: portal }),
    },
  });

  if (!response.ok) {
    throw await ApiError.fromResponse(response);
  }

  const payload = (await response.json()) as Partial<AccessTokenResponse>;

  if (
    typeof payload.access_token !== "string" ||
    payload.access_token.trim().length === 0
  ) {
    throw new ApiError(
      500,
      "The refresh response did not contain an access token.",
      payload,
    );
  }

  if (portal && payload.portal !== portal) {
    throw new ApiError(401, "The session belongs to a different portal.");
  }

  return payload.access_token;
}
