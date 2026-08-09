import {
  PORTALS,
  type AccessTokenClaims,
  type AuthSnapshot,
  type Portal,
} from "./types";

const PORTAL_PREFIXES: Record<Portal, string> = {
  CITIZEN: "/citizen",
  PROFESSIONAL: "/professional",
  ADMIN: "/admin",
};

export function isPortal(value: unknown): value is Portal {
  return (
    typeof value === "string" &&
    (PORTALS as readonly string[]).includes(value)
  );
}

export function portalForPathname(pathname: string): Portal | null {
  const normalizedPathname = pathname.startsWith("/")
    ? pathname
    : "/" + pathname;

  for (const portal of PORTALS) {
    const prefix = PORTAL_PREFIXES[portal];
    if (
      normalizedPathname === prefix ||
      normalizedPathname.startsWith(prefix + "/")
    ) {
      return portal;
    }
  }

  return null;
}

export function sessionMatchesPortal(
  sessionPortal: Portal | null,
  requiredPortal: Portal,
): boolean {
  return sessionPortal === requiredPortal;
}

export function canUsePathname(
  sessionPortal: Portal | null,
  pathname: string,
): boolean {
  const pathnamePortal = portalForPathname(pathname);

  return pathnamePortal === null || pathnamePortal === sessionPortal;
}

function decodeBase64Url(value: string): string {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const paddingLength = (4 - (normalized.length % 4)) % 4;

  return atob(normalized + "=".repeat(paddingLength));
}

export function decodeAccessTokenClaims(
  accessToken: string,
): AccessTokenClaims | null {
  try {
    const tokenParts = accessToken.split(".");
    if (tokenParts.length !== 3) {
      return null;
    }

    const payload = JSON.parse(decodeBase64Url(tokenParts[1])) as Record<
      string,
      unknown
    >;

    if (
      typeof payload.sub !== "string" ||
      payload.sub.length === 0 ||
      !isPortal(payload.portal) ||
      typeof payload.sid !== "string" ||
      payload.sid.length === 0 ||
      typeof payload.jti !== "string" ||
      payload.jti.length === 0 ||
      typeof payload.iat !== "number" ||
      typeof payload.exp !== "number" ||
      !Number.isFinite(payload.exp) ||
      payload.type !== "access"
    ) {
      return null;
    }

    return {
      sub: payload.sub,
      portal: payload.portal,
      sid: payload.sid,
      jti: payload.jti,
      exp: payload.exp,
      iat: payload.iat,
      type: "access",
    };
  } catch {
    return null;
  }
}

export function isAccessTokenExpired(
  claims: AccessTokenClaims,
  nowMs = Date.now(),
): boolean {
  return claims.exp * 1000 <= nowMs;
}

export function createAuthSnapshot(
  accessToken: string | null,
  nowMs = Date.now(),
): AuthSnapshot {
  const claims = accessToken ? decodeAccessTokenClaims(accessToken) : null;
  const isAuthenticated = claims !== null && !isAccessTokenExpired(claims, nowMs);

  return {
    status: isAuthenticated ? "authenticated" : "unauthenticated",
    accessToken,
    claims: isAuthenticated ? claims : null,
    portal: isAuthenticated ? claims.portal : null,
  };
}

// JWT decoding here is for frontend state and routing only. A decoded token is
// never treated as proof of authorization; the backend validates every request.
