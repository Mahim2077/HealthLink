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

  useEffect(() => {
    const claims = accessToken
      ? decodeAccessTokenClaims(accessToken)
      : null;

    if (claims === null) {
      return;
    }

    const expiresInMs = claims.exp * 1000 - Date.now();
    if (expiresInMs <= 0) {
      return;
    }

    const timer = window.setTimeout(
      () => setExpiryCheck((check) => check + 1),
      expiresInMs,
    );

    return () => window.clearTimeout(timer);
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
