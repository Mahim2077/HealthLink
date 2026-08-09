import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { accessTokenStore } from "@/lib/auth/token-store";

import { AuthProvider, usePortalAuth } from "./auth-provider";

function createCitizenToken(expiresInSeconds = 600): string {
  const issuedAt = Math.floor(Date.now() / 1000);
  const expiresAt = issuedAt + expiresInSeconds;
  const encode = (value: Record<string, unknown>) =>
    btoa(JSON.stringify(value))
      .replace(/=/g, "")
      .replace(/\+/g, "-")
      .replace(/\//g, "_");

  return (
    encode({ alg: "none", typ: "JWT" }) +
    "." +
    encode({
      sub: "citizen-1",
      portal: "CITIZEN",
      sid: "session-1",
      jti: "token-" + expiresAt,
      iat: issuedAt,
      exp: expiresAt,
      type: "access",
    }) +
    ".x"
  );
}

function AuthProbe() {
  const auth = usePortalAuth("CITIZEN");

  return (
    <div>
      <p>{auth.status}</p>
      <p>{auth.portal ?? "no-portal"}</p>
      <p>{auth.isRequiredPortal ? "portal-match" : "portal-mismatch"}</p>
      <button onClick={() => auth.setAccessToken(createCitizenToken())} type="button">
        Set token
      </button>
      <button onClick={auth.clearSession} type="button">
        Clear token
      </button>
    </div>
  );
}

describe("AuthProvider", () => {
  beforeEach(() => {
    accessTokenStore.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("reacts to the in-memory token and exposes portal-aware state", () => {
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );

    expect(screen.getByText("unauthenticated")).toBeInTheDocument();
    expect(screen.getByText("portal-mismatch")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Set token" }));

    expect(screen.getByText("authenticated")).toBeInTheDocument();
    expect(screen.getByText("CITIZEN")).toBeInTheDocument();
    expect(screen.getByText("portal-match")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Clear token" }));
    expect(screen.getByText("unauthenticated")).toBeInTheDocument();
  });

  it("expires an idle session and cancels the superseded expiry timer", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2030-01-01T00:00:00.000Z"));
    const { unmount } = render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );

    act(() => {
      accessTokenStore.set(createCitizenToken(5));
    });
    expect(screen.getByText("authenticated")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(2_000);
      accessTokenStore.set(createCitizenToken(20));
    });
    act(() => {
      vi.advanceTimersByTime(3_000);
    });
    expect(screen.getByText("authenticated")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(17_000);
    });
    expect(screen.getByText("unauthenticated")).toBeInTheDocument();

    unmount();
  });
});
