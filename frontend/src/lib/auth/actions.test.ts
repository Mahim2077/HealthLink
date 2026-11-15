import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({
  forPortal: vi.fn(),
  replaceSession: vi.fn(),
  refreshSession: vi.fn(),
  terminateSession: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  apiClientForPortal: apiMocks.forPortal,
}));

import {
  logout,
  logoutAll,
  refreshSession,
  replaceSession,
} from "./actions";

describe("auth session actions", () => {
  beforeEach(() => {
    apiMocks.forPortal.mockReset().mockReturnValue(apiMocks);
    apiMocks.replaceSession.mockReset();
    apiMocks.refreshSession.mockReset();
    apiMocks.terminateSession.mockReset();
  });

  it("delegates refresh to the single-flight API client", async () => {
    apiMocks.refreshSession.mockResolvedValue("fresh-token");

    await expect(refreshSession("CITIZEN")).resolves.toBe("fresh-token");
    expect(apiMocks.forPortal).toHaveBeenCalledWith("CITIZEN");
    expect(apiMocks.refreshSession).toHaveBeenCalledOnce();
  });

  it("runs logout through the session-mutation barrier", async () => {
    apiMocks.terminateSession.mockResolvedValue(undefined);

    await logout("PROFESSIONAL");

    expect(apiMocks.forPortal).toHaveBeenCalledWith("PROFESSIONAL");
    expect(apiMocks.terminateSession).toHaveBeenCalledWith("auth/logout");
  });

  it("runs logout-all through the session-mutation barrier", async () => {
    apiMocks.terminateSession.mockResolvedValue(undefined);

    await logoutAll("ADMIN");

    expect(apiMocks.forPortal).toHaveBeenCalledWith("ADMIN");
    expect(apiMocks.terminateSession).toHaveBeenCalledWith("auth/logout-all");
  });

  it("exposes serialized session replacement for a later login flow", async () => {
    const issueSession = vi.fn().mockResolvedValue("login-token");
    apiMocks.replaceSession.mockResolvedValue("login-token");

    await expect(replaceSession(issueSession, "PROFESSIONAL")).resolves.toBe("login-token");
    expect(apiMocks.replaceSession).toHaveBeenCalledWith(issueSession);
  });
});
