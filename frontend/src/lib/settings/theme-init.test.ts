import { beforeEach, expect, it, vi } from "vitest";
import { INTERFACE_PREFERENCES_KEY } from "./interface-preferences";
import { THEME_INIT_SCRIPT } from "./theme-init";

beforeEach(() => {
  vi.restoreAllMocks(); localStorage.clear();
  delete document.documentElement.dataset.theme;
  vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: true })));
});
it.each([["dark", "dark"], ["light", "light"], ["system", "dark"], ["unknown", "light"]])("initializes %s before hydration as %s", (choice, expected) => {
  localStorage.setItem(INTERFACE_PREFERENCES_KEY, JSON.stringify({ theme: choice }));
  new Function(THEME_INIT_SCRIPT)();
  expect(document.documentElement.dataset.theme).toBe(expected);
});
it("uses light with blocked/corrupt storage without throwing", () => {
  localStorage.setItem(INTERFACE_PREFERENCES_KEY, "not-json");
  new Function(THEME_INIT_SCRIPT)();
  expect(document.documentElement.dataset.theme).toBe("light");
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("blocked"); });
  expect(() => new Function(THEME_INIT_SCRIPT)()).not.toThrow();
  expect(document.documentElement.dataset.theme).toBe("light");
});
