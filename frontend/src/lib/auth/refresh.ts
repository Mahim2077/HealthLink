"use client";

import { buildApiUrl } from "@/lib/api/config";
import { ApiError } from "@/lib/api/errors";

import type { AccessTokenResponse } from "./types";

export async function requestAccessTokenRefresh(
  fetchImplementation: typeof fetch = fetch,
): Promise<string> {
  const response = await fetchImplementation(buildApiUrl("auth/refresh"), {
    method: "POST",
    credentials: "include",
    headers: {
      Accept: "application/json",
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

  return payload.access_token;
}
