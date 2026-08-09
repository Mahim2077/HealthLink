import { describe, expect, it } from "vitest";

import {
  canUsePathname,
  createAuthSnapshot,
  decodeAccessTokenClaims,
  portalForPathname,
} from "./portal";

function createUnsignedToken(payload: Record<string, unknown>): string {
  const encode = (value: Record<string, unknown>) =>
    btoa(JSON.stringify(value))
      .replace(/=/g, "")
      .replace(/\+/g, "-")
      .replace(/\//g, "_");

  return encode({ alg: "none", typ: "JWT" }) + "." + encode(payload) + ".x";
}

describe("portal-aware auth utilities", () => {
  it("decodes the minimum supported JWT claims", () => {
    const token = createUnsignedToken({
      sub: "user-123",
      portal: "CITIZEN",
      sid: "session-123",
      jti: "token-123",
      iat: 1_999_999_000,
      exp: 2_000_000_000,
      type: "access",
    });

    expect(decodeAccessTokenClaims(token)).toEqual({
      sub: "user-123",
      portal: "CITIZEN",
      sid: "session-123",
      jti: "token-123",
      exp: 2_000_000_000,
      iat: 1_999_999_000,
      type: "access",
    });
  });

  it("rejects malformed and unknown-portal tokens", () => {
    expect(decodeAccessTokenClaims("not-a-jwt")).toBeNull();
    expect(
      decodeAccessTokenClaims(
        createUnsignedToken({
          sub: "user-123",
          portal: "SUPERUSER",
          sid: "session-123",
          jti: "token-123",
          iat: 1_999_999_000,
          exp: 2_000_000_000,
          type: "access",
        }),
      ),
    ).toBeNull();
  });

  it("does not treat expired claims as an authenticated session", () => {
    const token = createUnsignedToken({
      sub: "user-123",
      portal: "ADMIN",
      sid: "session-123",
      jti: "token-123",
      iat: 10,
      exp: 100,
      type: "access",
    });

    expect(createAuthSnapshot(token, 101_000)).toMatchObject({
      status: "unauthenticated",
      claims: null,
      portal: null,
    });
  });

  it("maps portal paths without granting cross-portal navigation", () => {
    expect(portalForPathname("/professional/chamber")).toBe("PROFESSIONAL");
    expect(portalForPathname("/public-information")).toBeNull();
    expect(canUsePathname("CITIZEN", "/citizen/profile")).toBe(true);
    expect(canUsePathname("CITIZEN", "/admin/dashboard")).toBe(false);
  });
});
