"use client";

import { API_BASE_URL, joinApiUrl } from "./config";
import { ApiError } from "./errors";
import { requestAccessTokenRefresh } from "@/lib/auth/refresh";
import {
  AccessTokenStore,
  accessTokenStore,
} from "@/lib/auth/token-store";

function isRefreshEndpoint(path: string): boolean {
  const pathWithoutQuery = path.split(/[?#]/, 1)[0];
  const normalizedPath = pathWithoutQuery.replace(/^\/+|\/+$/g, "");

  return normalizedPath === "auth/refresh";
}

export type ApiRequestOptions = Omit<RequestInit, "body"> & {
  auth?: boolean;
  body?: BodyInit | null;
  json?: unknown;
  retryOnUnauthorized?: boolean;
};

type ApiClientOptions = {
  baseUrl?: string;
  fetchImplementation?: typeof fetch;
  refreshAccessToken?: () => Promise<string>;
  tokenStore?: AccessTokenStore;
};

export class AuthSessionChangedError extends Error {
  constructor() {
    super("Authentication state changed while the session was refreshing.");
    this.name = "AuthSessionChangedError";
  }
}

export class AuthSessionMutationInProgressError extends Error {
  constructor() {
    super("Authentication session mutation is in progress.");
    this.name = "AuthSessionMutationInProgressError";
  }
}

export class ApiClient {
  private readonly baseUrl: string;
  private readonly fetchImplementation: typeof fetch;
  private readonly refreshAccessTokenHandler: () => Promise<string>;
  private readonly tokenStore: AccessTokenStore;
  private pendingSessionMutations = 0;
  private refreshPromise: Promise<string> | null = null;
  private sessionMutationQueue: Promise<void> = Promise.resolve();

  constructor(options: ApiClientOptions = {}) {
    this.baseUrl = options.baseUrl ?? API_BASE_URL;
    this.fetchImplementation =
      options.fetchImplementation ?? globalThis.fetch.bind(globalThis);
    this.tokenStore = options.tokenStore ?? accessTokenStore;
    this.refreshAccessTokenHandler =
      options.refreshAccessToken ??
      (() => requestAccessTokenRefresh(this.fetchImplementation));
  }

  async request<TResponse>(
    path: string,
    options: ApiRequestOptions = {},
  ): Promise<TResponse> {
    return this.execute<TResponse>(path, options, true);
  }

  async get<TResponse>(
    path: string,
    options: Omit<ApiRequestOptions, "method"> = {},
  ): Promise<TResponse> {
    return this.request<TResponse>(path, { ...options, method: "GET" });
  }

  async post<TResponse, TBody = undefined>(
    path: string,
    body?: TBody,
    options: Omit<ApiRequestOptions, "json" | "method"> = {},
  ): Promise<TResponse> {
    return this.request<TResponse>(path, {
      ...options,
      method: "POST",
      ...(body === undefined ? {} : { json: body }),
    });
  }

  async put<TResponse, TBody>(
    path: string,
    body: TBody,
    options: Omit<ApiRequestOptions, "json" | "method"> = {},
  ): Promise<TResponse> {
    return this.request<TResponse>(path, {
      ...options,
      method: "PUT",
      json: body,
    });
  }

  async delete<TResponse>(
    path: string,
    options: Omit<ApiRequestOptions, "method"> = {},
  ): Promise<TResponse> {
    return this.request<TResponse>(path, { ...options, method: "DELETE" });
  }

  async refreshSession(): Promise<string> {
    return this.refreshOnce();
  }

  async terminateSession(
    path: "auth/logout" | "auth/logout-all",
  ): Promise<void> {
    const fallbackAccessToken = this.tokenStore.getSnapshot();

    await this.withSessionMutationBarrier(async () => {
      try {
        const terminationAccessToken =
          this.tokenStore.getSnapshot() ?? fallbackAccessToken;
        const headers = new Headers();
        if (terminationAccessToken !== null) {
          headers.set("Authorization", "Bearer " + terminationAccessToken);
        }

        await this.post<unknown>(path, undefined, {
          headers,
          retryOnUnauthorized: false,
        });
      } finally {
        this.tokenStore.clear();
      }
    });
  }

  async replaceSession(
    issueSession: () => Promise<string>,
  ): Promise<string> {
    return this.withSessionMutationBarrier(async () => {
      const accessToken = await issueSession();
      this.tokenStore.set(accessToken);
      return accessToken;
    });
  }

  private async execute<TResponse>(
    path: string,
    options: ApiRequestOptions,
    canRetry: boolean,
  ): Promise<TResponse> {
    const {
      auth = true,
      body,
      headers: providedHeaders,
      json,
      retryOnUnauthorized = true,
      ...requestInit
    } = options;

    if (body !== undefined && json !== undefined) {
      throw new Error("Use either body or json for an API request, not both.");
    }

    const headers = new Headers(providedHeaders);
    if (!headers.has("Accept")) {
      headers.set("Accept", "application/json");
    }

    const tokenUsed = auth ? this.tokenStore.getSnapshot() : null;
    if (tokenUsed) {
      headers.set("Authorization", "Bearer " + tokenUsed);
    }

    let requestBody = body;
    if (json !== undefined) {
      headers.set("Content-Type", "application/json");
      requestBody = JSON.stringify(json);
    }

    const response = await this.fetchImplementation(
      joinApiUrl(this.baseUrl, path),
      {
        ...requestInit,
        body: requestBody,
        credentials: requestInit.credentials ?? "include",
        headers,
      },
    );

    if (response.status === 401 && auth && retryOnUnauthorized && canRetry) {
      const currentToken = this.tokenStore.getSnapshot();

      if (currentToken !== tokenUsed) {
        if (currentToken !== null) {
          return this.execute<TResponse>(path, options, false);
        }
      } else if (!isRefreshEndpoint(path)) {
        await this.refreshOnce();
        return this.execute<TResponse>(path, options, false);
      }
    }

    if (!response.ok) {
      if (
        response.status === 401 &&
        auth &&
        this.pendingSessionMutations === 0
      ) {
        this.tokenStore.clearIfCurrent(tokenUsed);
      }

      throw await ApiError.fromResponse(response);
    }

    return this.parseResponse<TResponse>(response);
  }

  private async refreshOnce(): Promise<string> {
    if (this.refreshPromise !== null) {
      return this.refreshPromise;
    }

    if (this.pendingSessionMutations > 0) {
      throw new AuthSessionMutationInProgressError();
    }

    if (this.refreshPromise === null) {
      const refreshGeneration = this.tokenStore.getGeneration();

      this.refreshPromise = this.refreshAccessTokenHandler()
        .then((accessToken) => {
          if (
            this.tokenStore.setIfGeneration(refreshGeneration, accessToken)
          ) {
            return accessToken;
          }

          const currentToken = this.tokenStore.getSnapshot();
          if (currentToken !== null) {
            return currentToken;
          }

          throw new AuthSessionChangedError();
        })
        .catch((error: unknown) => {
          if (this.tokenStore.getGeneration() !== refreshGeneration) {
            const currentToken = this.tokenStore.getSnapshot();
            if (currentToken !== null) {
              return currentToken;
            }

            throw error;
          }

          this.tokenStore.clearIfGeneration(refreshGeneration);
          throw error;
        })
        .finally(() => {
          this.refreshPromise = null;
        });
    }

    return this.refreshPromise;
  }

  private async withSessionMutationBarrier<T>(
    mutation: () => Promise<T>,
  ): Promise<T> {
    this.pendingSessionMutations += 1;

    const previousMutation = this.sessionMutationQueue;
    let releaseMutation!: () => void;
    this.sessionMutationQueue = new Promise<void>((resolve) => {
      releaseMutation = resolve;
    });

    await previousMutation;

    try {
      const inFlightRefresh = this.refreshPromise;
      if (inFlightRefresh !== null) {
        try {
          await inFlightRefresh;
        } catch {
          // Termination/replacement still proceeds after a failed refresh so
          // local state and the server session can be resolved consistently.
        }
      }

      return await mutation();
    } finally {
      this.pendingSessionMutations -= 1;
      releaseMutation();
    }
  }

  private async parseResponse<TResponse>(
    response: Response,
  ): Promise<TResponse> {
    if (response.status === 204 || response.status === 205) {
      return undefined as TResponse;
    }

    const contentType = response.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      return (await response.json()) as TResponse;
    }

    return (await response.text()) as TResponse;
  }
}

export const apiClient = new ApiClient();
