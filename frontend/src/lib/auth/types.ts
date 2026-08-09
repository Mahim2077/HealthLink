export const PORTALS = ["CITIZEN", "PROFESSIONAL", "ADMIN"] as const;

export type Portal = (typeof PORTALS)[number];

export type AuthStatus = "authenticated" | "unauthenticated";

export type AccessTokenClaims = {
  sub: string;
  portal: Portal;
  sid: string;
  jti: string;
  exp: number;
  iat: number;
  type: "access";
};

export type AccessTokenResponse = {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  portal: Portal;
};

export type AuthSnapshot = {
  status: AuthStatus;
  accessToken: string | null;
  claims: AccessTokenClaims | null;
  portal: Portal | null;
};
