import { beforeEach, describe, expect, it, vi } from "vitest";

import { AccessTokenStore } from "@/lib/auth/token-store";

import {
  ApiClient,
  AuthSessionChangedError,
  AuthSessionMutationInProgressError,
} from "./client";
import { ApiError } from "./errors";

type Deferred<T> = {
  promise: Promise<T>;
  reject: (reason?: unknown) => void;
  resolve: (value: T | PromiseLike<T>) => void;
};

function createDeferred<T>(): Deferred<T> {
  let resolve!: Deferred<T>["resolve"];
  let reject!: Deferred<T>["reject"];
  const promise = new Promise<T>((promiseResolve, promiseReject) => {
    resolve = promiseResolve;
    reject = promiseReject;
  });

  return { promise, reject, resolve };
}

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    statusText: status === 401 ? "Unauthorized" : "OK",
    headers: { "content-type": "application/json" },
  });
}

describe("ApiClient", () => {
  let tokenStore: AccessTokenStore;

  beforeEach(() => {
    tokenStore = new AccessTokenStore();
  });

  it("binds the default fetch implementation to its global receiver", async () => {
    const receiverRequiredFetch = vi.fn(function (
      this: unknown,
    ): Promise<Response> {
      if (this !== globalThis) {
        throw new TypeError("fetch requires its global receiver");
      }

      return Promise.resolve(jsonResponse({ healthy: true }));
    }) as unknown as typeof fetch;
    vi.stubGlobal("fetch", receiverRequiredFetch);

    try {
      const client = new ApiClient({
        baseUrl: "https://api.healthlink.test/api/v1",
        refreshAccessToken: vi.fn(),
        tokenStore,
      });

      await expect(client.get<{ healthy: boolean }>("health")).resolves.toEqual(
        { healthy: true },
      );
      expect(receiverRequiredFetch).toHaveBeenCalledOnce();
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it("sends credentials, bearer auth, and parses a typed response", async () => {
    tokenStore.set("access-token");
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValue(jsonResponse({ healthy: true }));
    const client = new ApiClient({
      baseUrl: "https://api.healthlink.test/api/v1",
      fetchImplementation: fetchMock,
      refreshAccessToken: vi.fn(),
      tokenStore,
    });

    const result = await client.get<{ healthy: boolean }>("health");

    expect(result.healthy).toBe(true);
    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("https://api.healthlink.test/api/v1/health");
    expect(init?.credentials).toBe("include");
    expect(new Headers(init?.headers).get("Authorization")).toBe(
      "Bearer access-token",
    );
  });

  it("serializes typed JSON request bodies", async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(null, { status: 204 }));
    const client = new ApiClient({
      baseUrl: "https://api.healthlink.test/api/v1",
      fetchImplementation: fetchMock,
      refreshAccessToken: vi.fn(),
      tokenStore,
    });

    await client.post<void, { reason: string }>("example", {
      reason: "test",
    });

    const [, init] = fetchMock.mock.calls[0];
    expect(init?.body).toBe(JSON.stringify({ reason: "test" }));
    expect(new Headers(init?.headers).get("Content-Type")).toBe(
      "application/json",
    );
  });

  it("retries N concurrent 401 responses after one shared refresh", async () => {
    tokenStore.set("expired-token");
    const fetchMock = vi.fn<typeof fetch>(async (_input, init) => {
      const authorization = new Headers(init?.headers).get("Authorization");
      return authorization === "Bearer fresh-token"
        ? jsonResponse({ ok: true })
        : jsonResponse({ detail: "Expired" }, 401);
    });
    const refreshAccessToken = vi.fn().mockResolvedValue("fresh-token");
    const client = new ApiClient({
      baseUrl: "https://api.healthlink.test/api/v1",
      fetchImplementation: fetchMock,
      refreshAccessToken,
      tokenStore,
    });

    const results = await Promise.all(
      Array.from({ length: 6 }, (_, index) =>
        client.get<{ ok: boolean }>("records/" + index),
      ),
    );

    expect(results.every((result) => result.ok)).toBe(true);
    expect(refreshAccessToken).toHaveBeenCalledOnce();
    expect(tokenStore.getSnapshot()).toBe("fresh-token");
    expect(fetchMock).toHaveBeenCalledTimes(12);
  });

  it("retries a late stale 401 without rotating refresh twice", async () => {
    tokenStore.set("expired-token");
    let releaseLateResponse: (() => void) | undefined;
    const lateResponse = new Promise<void>((resolve) => {
      releaseLateResponse = resolve;
    });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const authorization = new Headers(init?.headers).get("Authorization");

      if (authorization === "Bearer fresh-token") {
        return jsonResponse({ ok: true });
      }

      if (String(input).endsWith("/records/late")) {
        await lateResponse;
      }

      return jsonResponse({ detail: "Expired" }, 401);
    });
    const refreshAccessToken = vi.fn().mockResolvedValue("fresh-token");
    const client = new ApiClient({
      baseUrl: "https://api.healthlink.test/api/v1",
      fetchImplementation: fetchMock,
      refreshAccessToken,
      tokenStore,
    });

    const firstRequest = client.get<{ ok: boolean }>("records/first");
    const lateRequest = client.get<{ ok: boolean }>("records/late");

    await expect(firstRequest).resolves.toEqual({ ok: true });
    releaseLateResponse?.();
    await expect(lateRequest).resolves.toEqual({ ok: true });

    expect(refreshAccessToken).toHaveBeenCalledOnce();
    expect(fetchMock).toHaveBeenCalledTimes(4);
  });

  it.each(["auth/logout", "auth/logout-all"] as const)(
    "%s waits for an in-flight refresh and uses its latest bearer",
    async (terminationPath) => {
      tokenStore.set("expired-token");
      const refreshStarted = createDeferred<void>();
      const refreshResult = createDeferred<string>();
      const events: string[] = [];
      let terminationAuthorization: string | null = null;
      const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
        const url = String(input);
        const authorization = new Headers(init?.headers).get("Authorization");

        if (url.endsWith("/protected")) {
          if (authorization === "Bearer fresh-token") {
            events.push("protected-retry");
            return jsonResponse({ ok: true });
          }

          events.push("protected-401");
          return jsonResponse({ detail: "Expired" }, 401);
        }

        if (url.endsWith("/" + terminationPath)) {
          events.push("termination-fetch");
          terminationAuthorization = authorization;
          return jsonResponse({ detail: "Terminated" });
        }

        throw new Error("Unexpected URL: " + url);
      });
      const client = new ApiClient({
        baseUrl: "https://api.healthlink.test/api/v1",
        fetchImplementation: fetchMock,
        refreshAccessToken: vi.fn(() => {
          events.push("refresh-start");
          refreshStarted.resolve();
          return refreshResult.promise.then((token) => {
            events.push("refresh-finish");
            return token;
          });
        }),
        tokenStore,
      });

      const protectedRequest = client.get<{ ok: boolean }>("protected");
      await refreshStarted.promise;
      const termination = client.terminateSession(terminationPath);
      await Promise.resolve();

      expect(events).not.toContain("termination-fetch");

      refreshResult.resolve("fresh-token");
      await expect(protectedRequest).resolves.toEqual({ ok: true });
      await expect(termination).resolves.toBeUndefined();

      expect(events.indexOf("refresh-finish")).toBeLessThan(
        events.indexOf("termination-fetch"),
      );
      expect(terminationAuthorization).toBe("Bearer fresh-token");
      expect(tokenStore.getSnapshot()).toBeNull();
    },
  );

  it("blocks new refresh starts while session termination is active", async () => {
    tokenStore.set("access-token");
    const terminationStarted = createDeferred<void>();
    const releaseTermination = createDeferred<void>();
    const fetchMock = vi.fn<typeof fetch>(async (input) => {
      const url = String(input);

      if (url.endsWith("/auth/logout")) {
        terminationStarted.resolve();
        await releaseTermination.promise;
        return jsonResponse({ detail: "Logged out" });
      }

      return jsonResponse({ detail: "Expired" }, 401);
    });
    const refreshAccessToken = vi.fn().mockResolvedValue("unexpected-token");
    const client = new ApiClient({
      baseUrl: "https://api.healthlink.test/api/v1",
      fetchImplementation: fetchMock,
      refreshAccessToken,
      tokenStore,
    });

    const termination = client.terminateSession("auth/logout");
    await terminationStarted.promise;

    await expect(client.get("protected")).rejects.toBeInstanceOf(
      AuthSessionMutationInProgressError,
    );
    expect(refreshAccessToken).not.toHaveBeenCalled();

    await expect(
      client.get("protected", { retryOnUnauthorized: false }),
    ).rejects.toMatchObject({ status: 401 });
    expect(tokenStore.getSnapshot()).toBe("access-token");

    releaseTermination.resolve();
    await termination;
    expect(tokenStore.getSnapshot()).toBeNull();
  });

  it("uses the captured bearer if an in-flight refresh fails", async () => {
    tokenStore.set("captured-valid-token");
    const refreshStarted = createDeferred<void>();
    const refreshResult = createDeferred<string>();
    let terminationAuthorization: string | null = null;
    const fetchMock = vi.fn<typeof fetch>(async (_input, init) => {
      terminationAuthorization = new Headers(init?.headers).get(
        "Authorization",
      );
      return jsonResponse({ detail: "Logged out from all sessions" });
    });
    const client = new ApiClient({
      baseUrl: "https://api.healthlink.test/api/v1",
      fetchImplementation: fetchMock,
      refreshAccessToken: vi.fn(() => {
        refreshStarted.resolve();
        return refreshResult.promise;
      }),
      tokenStore,
    });

    const refresh = client.refreshSession();
    await refreshStarted.promise;
    const termination = client.terminateSession("auth/logout-all");

    refreshResult.reject(new Error("Refresh unavailable"));

    await expect(refresh).rejects.toThrow("Refresh unavailable");
    await expect(termination).resolves.toBeUndefined();
    expect(terminationAuthorization).toBe("Bearer captured-valid-token");
    expect(tokenStore.getSnapshot()).toBeNull();
  });

  it("serializes future session replacements through the same barrier", async () => {
    const firstReplacementStarted = createDeferred<void>();
    const releaseFirstReplacement = createDeferred<void>();
    const events: string[] = [];
    const refreshAccessToken = vi.fn().mockResolvedValue("unexpected-token");
    const client = new ApiClient({
      baseUrl: "https://api.healthlink.test/api/v1",
      fetchImplementation: vi.fn(),
      refreshAccessToken,
      tokenStore,
    });

    const firstReplacement = client.replaceSession(async () => {
      events.push("first-start");
      firstReplacementStarted.resolve();
      await releaseFirstReplacement.promise;
      events.push("first-finish");
      return "first-session-token";
    });
    await firstReplacementStarted.promise;

    const secondReplacement = client.replaceSession(async () => {
      events.push("second-start");
      return "second-session-token";
    });
    await Promise.resolve();

    expect(events).toEqual(["first-start"]);
    await expect(client.refreshSession()).rejects.toBeInstanceOf(
      AuthSessionMutationInProgressError,
    );
    expect(refreshAccessToken).not.toHaveBeenCalled();

    releaseFirstReplacement.resolve();

    await expect(firstReplacement).resolves.toBe("first-session-token");
    await expect(secondReplacement).resolves.toBe("second-session-token");
    expect(events).toEqual([
      "first-start",
      "first-finish",
      "second-start",
    ]);
    expect(tokenStore.getSnapshot()).toBe("second-session-token");
  });

  it("clears in-memory auth when refresh fails", async () => {
    tokenStore.set("expired-token");
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValue(jsonResponse({ detail: "Expired" }, 401));
    const client = new ApiClient({
      baseUrl: "https://api.healthlink.test/api/v1",
      fetchImplementation: fetchMock,
      refreshAccessToken: vi.fn().mockRejectedValue(new Error("No session")),
      tokenStore,
    });

    await expect(client.get("protected")).rejects.toThrow("No session");
    expect(tokenStore.getSnapshot()).toBeNull();
  });

  it("does not resurrect a token when refresh succeeds after clear", async () => {
    tokenStore.set("expired-token");
    const refreshStarted = createDeferred<void>();
    const refreshResult = createDeferred<string>();
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValue(jsonResponse({ detail: "Expired" }, 401));
    const client = new ApiClient({
      baseUrl: "https://api.healthlink.test/api/v1",
      fetchImplementation: fetchMock,
      refreshAccessToken: vi.fn(() => {
        refreshStarted.resolve();
        return refreshResult.promise;
      }),
      tokenStore,
    });

    const request = client.get("protected");
    await refreshStarted.promise;
    tokenStore.clear();
    refreshResult.resolve("stale-refresh-token");

    await expect(request).rejects.toBeInstanceOf(AuthSessionChangedError);
    expect(tokenStore.getSnapshot()).toBeNull();
  });

  it("does not let stale refresh failure clear a newer login", async () => {
    tokenStore.set("expired-token");
    const refreshStarted = createDeferred<void>();
    const refreshResult = createDeferred<string>();
    const fetchMock = vi.fn<typeof fetch>(async (_input, init) => {
      const authorization = new Headers(init?.headers).get("Authorization");
      return authorization === "Bearer newer-login-token"
        ? jsonResponse({ ok: true })
        : jsonResponse({ detail: "Expired" }, 401);
    });
    const client = new ApiClient({
      baseUrl: "https://api.healthlink.test/api/v1",
      fetchImplementation: fetchMock,
      refreshAccessToken: vi.fn(() => {
        refreshStarted.resolve();
        return refreshResult.promise;
      }),
      tokenStore,
    });

    const request = client.get<{ ok: boolean }>("protected");
    await refreshStarted.promise;
    tokenStore.set("newer-login-token");
    refreshResult.reject(new Error("Old refresh rejected"));

    await expect(request).resolves.toEqual({ ok: true });
    expect(tokenStore.getSnapshot()).toBe("newer-login-token");
  });

  it("does not let a late final 401 clear a newer token", async () => {
    tokenStore.set("request-token");
    const responseStarted = createDeferred<void>();
    const releaseResponse = createDeferred<void>();
    const fetchMock = vi.fn<typeof fetch>(async () => {
      responseStarted.resolve();
      await releaseResponse.promise;
      return jsonResponse({ detail: "Expired" }, 401);
    });
    const client = new ApiClient({
      baseUrl: "https://api.healthlink.test/api/v1",
      fetchImplementation: fetchMock,
      refreshAccessToken: vi.fn(),
      tokenStore,
    });

    const request = client.get("protected", { retryOnUnauthorized: false });
    await responseStarted.promise;
    tokenStore.set("newer-login-token");
    releaseResponse.resolve();

    await expect(request).rejects.toMatchObject({ status: 401 });
    expect(tokenStore.getSnapshot()).toBe("newer-login-token");
  });

  it("does not refresh requests explicitly marked public", async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValue(jsonResponse({ detail: "Invalid credentials" }, 401));
    const refreshAccessToken = vi.fn();
    const client = new ApiClient({
      baseUrl: "https://api.healthlink.test/api/v1",
      fetchImplementation: fetchMock,
      refreshAccessToken,
      tokenStore,
    });

    await expect(
      client.post("auth/example-login", undefined, { auth: false }),
    ).rejects.toBeInstanceOf(ApiError);
    expect(refreshAccessToken).not.toHaveBeenCalled();
  });

  it("does not refresh or retry a forbidden response", async () => {
    tokenStore.set("access-token");
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValue(jsonResponse({ detail: "Forbidden" }, 403));
    const refreshAccessToken = vi.fn();
    const client = new ApiClient({
      baseUrl: "https://api.healthlink.test/api/v1",
      fetchImplementation: fetchMock,
      refreshAccessToken,
      tokenStore,
    });

    await expect(client.get("admin-only")).rejects.toMatchObject({
      status: 403,
      message: "Forbidden",
    });
    expect(refreshAccessToken).not.toHaveBeenCalled();
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it("never auto-refreshes the refresh endpoint itself", async () => {
    tokenStore.set("expired-token");
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValue(jsonResponse({ detail: "Refresh rejected" }, 401));
    const refreshAccessToken = vi.fn();
    const client = new ApiClient({
      baseUrl: "https://api.healthlink.test/api/v1",
      fetchImplementation: fetchMock,
      refreshAccessToken,
      tokenStore,
    });

    await expect(client.get("/auth/refresh?source=retry")).rejects.toMatchObject(
      {
        status: 401,
        message: "Refresh rejected",
      },
    );
    expect(refreshAccessToken).not.toHaveBeenCalled();
    expect(fetchMock).toHaveBeenCalledOnce();
  });
});
