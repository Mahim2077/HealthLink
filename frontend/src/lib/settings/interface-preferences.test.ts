import { beforeEach, expect, it, vi } from "vitest";
import { DEFAULT_INTERFACE_PREFERENCES, INTERFACE_PREFERENCES_KEY, parseInterfacePreferences, saveInterfacePreferences } from "./interface-preferences";

beforeEach(() => { vi.restoreAllMocks(); localStorage.clear(); });
it.each([null, "invalid", "null", "42", "[]", '{"textSize":"other","motion":"spin","navigation":"wide"}'])("safely defaults invalid preferences %s", raw => {
  expect(parseInterfacePreferences(raw)).toEqual(DEFAULT_INTERFACE_PREFERENCES);
});
it("persists only the allowlisted display fields", () => {
  const value = { textSize: "large", motion: "reduced", navigation: "expanded", theme: "dark", medicalRecord: "must not persist" };
  expect(saveInterfacePreferences(value as typeof DEFAULT_INTERFACE_PREFERENCES)).toBe(true);
  expect(JSON.parse(localStorage.getItem(INTERFACE_PREFERENCES_KEY)!)).toEqual({ textSize: "large", motion: "reduced", navigation: "expanded", theme: "dark" });
});
it("preserves legacy display settings and defaults an absent/unknown theme to light", () => {
  expect(parseInterfacePreferences('{"textSize":"large","theme":"sepia"}')).toEqual({ ...DEFAULT_INTERFACE_PREFERENCES, textSize: "large" });
});
it("reports unavailable browser storage without crashing", () => {
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("blocked"); });
  expect(saveInterfacePreferences(DEFAULT_INTERFACE_PREFERENCES)).toBe(false);
});
