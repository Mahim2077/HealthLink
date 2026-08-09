import { describe, expect, it, vi } from "vitest";

import { AccessTokenStore } from "./token-store";

describe("AccessTokenStore", () => {
  it("keeps the token in memory and notifies subscribers", () => {
    const store = new AccessTokenStore();
    const listener = vi.fn();
    const unsubscribe = store.subscribe(listener);

    store.set("access-token");

    expect(store.getSnapshot()).toBe("access-token");
    expect(listener).toHaveBeenCalledOnce();

    unsubscribe();
    store.clear();
    expect(listener).toHaveBeenCalledOnce();
  });

  it("rejects an empty token", () => {
    const store = new AccessTokenStore();

    expect(() => store.set("   ")).toThrow("Access token cannot be empty");
  });

  it("never writes access tokens to browser storage", () => {
    const localStorageWrite = vi.spyOn(Storage.prototype, "setItem");
    const localStorageRead = vi.spyOn(Storage.prototype, "getItem");
    const store = new AccessTokenStore();

    store.set("memory-only-token");
    expect(store.getSnapshot()).toBe("memory-only-token");

    expect(localStorageWrite).not.toHaveBeenCalled();
    expect(localStorageRead).not.toHaveBeenCalled();

    localStorageWrite.mockRestore();
    localStorageRead.mockRestore();
  });

  it("uses generations for conditional refresh mutations", () => {
    const store = new AccessTokenStore();
    store.set("original-token");
    const refreshGeneration = store.getGeneration();

    store.clear();

    expect(store.setIfGeneration(refreshGeneration, "stale-refresh")).toBe(
      false,
    );
    expect(store.clearIfGeneration(refreshGeneration)).toBe(false);
    expect(store.getSnapshot()).toBeNull();
  });

  it("clears conditionally only when the expected token is still current", () => {
    const store = new AccessTokenStore();
    store.set("new-login-token");

    expect(store.clearIfCurrent("older-token")).toBe(false);
    expect(store.getSnapshot()).toBe("new-login-token");
    expect(store.clearIfCurrent("new-login-token")).toBe(true);
    expect(store.getSnapshot()).toBeNull();
  });
});
