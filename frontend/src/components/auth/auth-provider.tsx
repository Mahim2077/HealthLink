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
import { portalTokenStores } from "@/lib/auth/token-store";
import type { AuthSnapshot, Portal } from "@/lib/auth/types";

type AuthContextValue = AuthSnapshot & {
  clearSession: () => void;
  logout: () => Promise<void>;
  logoutAll: () => Promise<void>;
  refreshSession: () => Promise<string>;
  setAccessToken: (accessToken: string) => void;
};

const AuthContext = createContext<Record<Portal, AuthContextValue> | null>(null);

function usePortalSession(portal: Portal): AuthContextValue {
  const store = portalTokenStores[portal];
  const [, setExpiryCheck] = useState(0);
  const accessToken = useSyncExternalStore(
    store.subscribe,
    store.getSnapshot,
    store.getServerSnapshot,
  );

  const setAccessToken = useCallback((token: string) => {
    store.set(token);
  }, [store]);

  const clearSession = useCallback(() => {
    store.clear();
  }, [store]);

  const refresh = useCallback(() => refreshSession(portal), [portal]);
  const signOut = useCallback(() => logout(portal), [portal]);
  const signOutAll = useCallback(() => logoutAll(portal), [portal]);

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
      void refresh().catch((error: unknown) => {
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
  }, [accessToken, refresh]);

  return {
    ...createAuthSnapshot(accessToken),
    clearSession,
    logout: signOut,
    logoutAll: signOutAll,
    refreshSession: refresh,
    setAccessToken,
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const citizen = usePortalSession("CITIZEN");
  const professional = usePortalSession("PROFESSIONAL");
  const admin = usePortalSession("ADMIN");
  useEffect(subscribeToSessionChanges, []);
  const value = { CITIZEN: citizen, PROFESSIONAL: professional, ADMIN: admin };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function usePortalAuth(requiredPortal: Portal) {
  const context = useContext(AuthContext);

  if (context === null) {
    throw new Error("usePortalAuth must be used within an AuthProvider.");
  }

  const auth = context[requiredPortal];
  return {
    ...auth,
    isRequiredPortal: sessionMatchesPortal(auth.portal, requiredPortal),
  };
}
