import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({
  replaceSession: vi.fn(),
  refreshSession: vi.fn(),
  terminateSession: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  apiClient: apiMocks,
}));

import {
  logout,
  logoutAll,
  refreshSession,
  replaceSession,
} from "./actions";

describe("auth session actions", () => {
  beforeEach(() => {
    apiMocks.replaceSession.mockReset();
    apiMocks.refreshSession.mockReset();
    apiMocks.terminateSession.mockReset();
  });

  it("delegates refresh to the single-flight API client", async () => {
    apiMocks.refreshSession.mockResolvedValue("fresh-token");

    await expect(refreshSession()).resolves.toBe("fresh-token");
    expect(apiMocks.refreshSession).toHaveBeenCalledOnce();
  });

  it("runs logout through the session-mutation barrier", async () => {
    apiMocks.terminateSession.mockResolvedValue(undefined);

    await logout();

    expect(apiMocks.terminateSession).toHaveBeenCalledWith("auth/logout");
  });

  it("runs logout-all through the session-mutation barrier", async () => {
    apiMocks.terminateSession.mockResolvedValue(undefined);

    await logoutAll();

    expect(apiMocks.terminateSession).toHaveBeenCalledWith("auth/logout-all");
  });

  it("exposes serialized session replacement for a later login flow", async () => {
    const issueSession = vi.fn().mockResolvedValue("login-token");
    apiMocks.replaceSession.mockResolvedValue("login-token");

    await expect(replaceSession(issueSession)).resolves.toBe("login-token");
    expect(apiMocks.replaceSession).toHaveBeenCalledWith(issueSession);
  });
});
