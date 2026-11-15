"use client";

import { API_BASE_URL, joinApiUrl } from "./config";
import { ApiError } from "./errors";
import { requestAccessTokenRefresh, SESSION_PORTAL_HEADER } from "@/lib/auth/refresh";
import { decodeAccessTokenClaims, isPortal, portalForPathname } from "@/lib/auth/portal";
import {
  AccessTokenStore,
  accessTokenStore,
  portalTokenStores,
} from "@/lib/auth/token-store";
import { PORTALS, type Portal } from "@/lib/auth/types";

const SESSION_CHANNEL = "healthlink:session";
let browserSessionChannel: BroadcastChannel | undefined;

type SessionChange = { portal: Portal; accountId?: string };

function clearChangedSessions({ portal, accountId }: SessionChange) {
  for (const candidate of PORTALS) {
    const store = portalTokenStores[candidate];
    const token = store.getSnapshot();
    if (candidate === portal || (accountId && token && decodeAccessTokenClaims(token)?.sub === accountId)) {
      store.clear();
    }
  }
}

async function withBrowserSessionLock<T>(run: () => Promise<T>): Promise<T> {
  return typeof navigator !== "undefined" && navigator.locks
    ? navigator.locks.request(SESSION_CHANNEL, run)
    : run();
}

function sessionChannel(): BroadcastChannel | undefined {
  if (typeof window === "undefined" || !window.BroadcastChannel) return;
  browserSessionChannel ??= new window.BroadcastChannel(SESSION_CHANNEL);
  return browserSessionChannel;
}

export function subscribeToSessionChanges(): () => void {
  const channel = sessionChannel();
  const onMessage = (event: MessageEvent<Partial<SessionChange> | null>) => {
    if (isPortal(event.data?.portal)) {
      clearChangedSessions({
        portal: event.data.portal,
        accountId: typeof event.data.accountId === "string" ? event.data.accountId : undefined,
      });
    }
  };
  channel?.addEventListener("message", onMessage);
  return () => channel?.removeEventListener("message", onMessage);
}

function isRefreshEndpoint(path: string): boolean {
  const pathWithoutQuery = path.split(/[?#]/, 1)[0];
  const normalizedPath = pathWithoutQuery.replace(/^\/+|\/+$/g, "");

  return normalizedPath === "auth/refresh";
}

export type ApiRequestOptions = Omit<RequestInit, "body"> & {
  auth?: boolean;
  body?: BodyInit | null;
  json?: unknown;
  portal?: Portal;
  retryOnUnauthorized?: boolean;
};

type ApiClientOptions = {
  baseUrl?: string;
  fetchImplementation?: typeof fetch;
  refreshAccessToken?: () => Promise<string>;
  tokenStore?: AccessTokenStore;
  portal?: Portal;
  routeRequests?: boolean;
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
  private readonly portal?: Portal;
  private readonly routeRequests: boolean;
  private pendingSessionMutations = 0;
  private refreshPromise: Promise<string> | null = null;
  private sessionMutationQueue: Promise<void> = Promise.resolve();

  constructor(options: ApiClientOptions = {}) {
    this.baseUrl = options.baseUrl ?? API_BASE_URL;
    this.fetchImplementation =
      options.fetchImplementation ?? globalThis.fetch.bind(globalThis);
    this.portal = options.portal;
    this.routeRequests = options.routeRequests ?? false;
    this.tokenStore = options.tokenStore ?? (this.portal ? portalTokenStores[this.portal] : accessTokenStore);
    this.refreshAccessTokenHandler =
      options.refreshAccessToken ??
      (() => requestAccessTokenRefresh(this.fetchImplementation, this.portal));
  }

  async request<TResponse>(
    path: string,
    { portal, ...options }: ApiRequestOptions = {},
  ): Promise<TResponse> {
    if (this.routeRequests) {
      const requestPortal = portal ?? (typeof window === "undefined" ? null : portalForPathname(window.location.pathname));
      if (requestPortal) return apiClientForPortal(requestPortal).request<TResponse>(path, options);
    }
    return this.execute<TResponse>(path, options, true);
  }

  async get<TResponse>(
    path: string,
    options: Omit<ApiRequestOptions, "method"> = {},
  ): Promise<TResponse> {
    return this.request<TResponse>(path, { ...options, method: "GET" });
  }

  async getBlob(
    path: string,
    options: Omit<ApiRequestOptions, "method"> = {},
  ): Promise<Blob> {
    const headers = new Headers(options.headers);
    headers.set("Accept", "application/pdf");
    return this.request<Blob>(path, {
      ...options,
      headers,
      method: "GET",
    });
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
        if (this.portal) {
          const accountId = path === "auth/logout-all" && terminationAccessToken
            ? decodeAccessTokenClaims(terminationAccessToken)?.sub
            : undefined;
          const change = { portal: this.portal, accountId };
          clearChangedSessions(change);
          sessionChannel()?.postMessage(change);
        }
      } finally {
        this.tokenStore.clear();
      }
    });
  }

  async replaceSession<T extends string | { access_token: string }>(
    issueSession: () => Promise<T>,
  ): Promise<T> {
    return this.withSessionMutationBarrier(async () => {
      const result = await issueSession();
      this.tokenStore.set(typeof result === "string" ? result : result.access_token);
      if (this.portal) sessionChannel()?.postMessage({ portal: this.portal });
      return result;
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
    if (this.portal && path.startsWith("auth/")) {
      headers.set(SESSION_PORTAL_HEADER, this.portal);
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
          const previousSession = tokenUsed && decodeAccessTokenClaims(tokenUsed)?.sid;
          const currentSession = decodeAccessTokenClaims(currentToken)?.sid;
          if (!previousSession || previousSession === currentSession) {
            return this.execute<TResponse>(path, options, false);
          }
        }
      } else if (!isRefreshEndpoint(path)) {
        const refreshedToken = await this.refreshOnce();
        const previousSession = tokenUsed && decodeAccessTokenClaims(tokenUsed)?.sid;
        if (!previousSession || previousSession === decodeAccessTokenClaims(refreshedToken)?.sid) {
          return this.execute<TResponse>(path, options, false);
        }
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

      this.refreshPromise = withBrowserSessionLock(this.refreshAccessTokenHandler)
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

          if (error instanceof ApiError && error.status === 401) {
            this.tokenStore.clearIfGeneration(refreshGeneration);
          }
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

      return await withBrowserSessionLock(mutation);
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

    if (contentType.includes("application/pdf")) {
      return (await response.blob()) as TResponse;
    }

    return (await response.text()) as TResponse;
  }
}

const portalClients: Record<Portal, ApiClient> = {
  CITIZEN: new ApiClient({ portal: "CITIZEN" }),
  PROFESSIONAL: new ApiClient({ portal: "PROFESSIONAL" }),
  ADMIN: new ApiClient({ portal: "ADMIN" }),
};

export function apiClientForPortal(portal: Portal): ApiClient {
  return portalClients[portal];
}

export const apiClient = new ApiClient({ routeRequests: true });
