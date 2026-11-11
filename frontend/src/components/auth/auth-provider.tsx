"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";

import { logout, logoutAll, refreshSession } from "@/lib/auth/actions";
import { subscribeToSessionChanges } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import {
  createAuthSnapshot,
  decodeAccessTokenClaims,
  sessionMatchesPortal,
} from "@/lib/auth/portal";
import { accessTokenStore } from "@/lib/auth/token-store";
import type { AuthSnapshot, Portal } from "@/lib/auth/types";

type AuthContextValue = AuthSnapshot & {
  clearSession: () => void;
  logout: () => Promise<void>;
  logoutAll: () => Promise<void>;
  refreshSession: () => Promise<string>;
  setAccessToken: (accessToken: string) => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [, setExpiryCheck] = useState(0);
  const accessToken = useSyncExternalStore(
    accessTokenStore.subscribe,
    accessTokenStore.getSnapshot,
    accessTokenStore.getServerSnapshot,
  );

  const setAccessToken = useCallback((token: string) => {
    accessTokenStore.set(token);
  }, []);

  const clearSession = useCallback(() => {
    accessTokenStore.clear();
  }, []);

  useEffect(() => subscribeToSessionChanges(clearSession), [clearSession]);

  useEffect(() => {
    const claims = accessToken
      ? decodeAccessTokenClaims(accessToken)
      : null;

    if (claims === null) {
      return;
    }

    const expiresInMs = claims.exp * 1000 - Date.now();
    if (expiresInMs <= 0) return;
    const refreshAhead = Math.min(60_000, (claims.exp - claims.iat) * 100);
    let active = true;
    let retry: number | undefined;
    const renew = () => {
      if (document.visibilityState === "hidden") return;
      window.clearTimeout(retry);
      void refreshSession().catch((error: unknown) => {
        if (!active || (error instanceof ApiError && error.status === 401)) return;
        retry = window.setTimeout(renew, 15_000);
      });
    };
    const checkOnReturn = () => {
      if (claims.exp * 1000 - Date.now() <= refreshAhead) renew();
    };
    const timer = window.setTimeout(renew, Math.max(0, expiresInMs - refreshAhead));
    const expiry = window.setTimeout(
      () => setExpiryCheck((check) => check + 1),
      expiresInMs,
    );
    document.addEventListener("visibilitychange", checkOnReturn);
    window.addEventListener("online", checkOnReturn);
    return () => {
      active = false;
      window.clearTimeout(timer);
      window.clearTimeout(retry);
      window.clearTimeout(expiry);
      document.removeEventListener("visibilitychange", checkOnReturn);
      window.removeEventListener("online", checkOnReturn);
    };
  }, [accessToken]);

  const value: AuthContextValue = {
    ...createAuthSnapshot(accessToken),
    clearSession,
    logout,
    logoutAll,
    refreshSession,
    setAccessToken,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);

  if (context === null) {
    throw new Error("useAuth must be used within an AuthProvider.");
  }

  return context;
}

export function usePortalAuth(requiredPortal: Portal) {
  const auth = useAuth();

  return {
    ...auth,
    isRequiredPortal: sessionMatchesPortal(auth.portal, requiredPortal),
  };
}
