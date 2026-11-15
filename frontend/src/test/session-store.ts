import { decodeAccessTokenClaims } from "@/lib/auth/portal";
import { portalTokenStores } from "@/lib/auth/token-store";
import { PORTALS } from "@/lib/auth/types";

export const testSessionStore = {
  set(token: string) {
    const claims = decodeAccessTokenClaims(token);
    if (!claims) throw new Error("Expected a valid test access token.");
    portalTokenStores[claims.portal].set(token);
  },
  clear() {
    for (const portal of PORTALS) portalTokenStores[portal].clear();
  },
};
