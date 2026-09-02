import { describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/errors";

import { requestAccessTokenRefresh } from "./refresh";

describe("refresh request", () => {
  it("uses the HttpOnly-cookie credential flow and returns the access token", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({ access_token: "fresh-token", token_type: "bearer" }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        },
      ),
    );

    await expect(requestAccessTokenRefresh(fetchMock)).resolves.toBe(
      "fresh-token",
    );
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/v1\/auth\/refresh$/),
      expect.objectContaining({
        method: "POST",
        credentials: "include",
      }),
    );
  });

  it("surfaces a typed API error when refresh is rejected", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ detail: "Session expired" }), {
        status: 401,
        statusText: "Unauthorized",
        headers: { "content-type": "application/json" },
      }),
    );

    const error = await requestAccessTokenRefresh(fetchMock).catch(
      (refreshError: unknown) => refreshError,
    );

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 401,
      message: "Session expired",
    });
  });
});
