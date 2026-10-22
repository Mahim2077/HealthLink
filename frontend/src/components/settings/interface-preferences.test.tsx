import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { INTERFACE_PREFERENCES_KEY } from "@/lib/settings/interface-preferences";
import { DisplaySettings, InterfacePreferencesBridge } from "./interface-preferences";

beforeEach(() => {
  vi.restoreAllMocks(); localStorage.clear();
  vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() })));
});
it("applies text/motion changes immediately, stores them and resets", async () => {
  render(<><InterfacePreferencesBridge /><DisplaySettings /></>);
  fireEvent.change(screen.getByRole("combobox", { name: /^Text size/ }), { target: { value: "large" } });
  fireEvent.change(screen.getByRole("combobox", { name: /^Motion/ }), { target: { value: "reduced" } });
  await waitFor(() => expect(document.documentElement.dataset.textSize).toBe("large"));
  expect(document.documentElement.dataset.motion).toBe("reduced");
  expect(screen.getByRole("status")).toHaveTextContent("on this device");
  fireEvent.click(screen.getByRole("button", { name: "Reset display preferences" }));
  expect(document.documentElement.dataset.textSize).toBe("standard");
  expect(document.documentElement.dataset.motion).toBe("system");
  expect(document.documentElement.dataset.theme).toBe("light");
});
it("switches light/dark themes, then follows live system changes only in System mode", () => {
  const listeners = new Set<() => void>();
  const media = { matches: false, addEventListener: vi.fn((_event, listener) => listeners.add(listener)), removeEventListener: vi.fn((_event, listener) => listeners.delete(listener)) };
  vi.mocked(window.matchMedia).mockReturnValue(media as unknown as MediaQueryList);
  const view = render(<><InterfacePreferencesBridge /><DisplaySettings /></>);
  const selector = screen.getByRole("combobox", { name: /^Color theme/ });
  fireEvent.change(selector, { target: { value: "dark" } });
  expect(document.documentElement.dataset.theme).toBe("dark");
  act(() => { media.matches = false; listeners.forEach(listener => listener()); });
  expect(document.documentElement.dataset.theme).toBe("dark");
  fireEvent.change(selector, { target: { value: "system" } });
  expect(document.documentElement.dataset.theme).toBe("light");
  act(() => { media.matches = true; listeners.forEach(listener => listener()); });
  expect(document.documentElement.dataset.theme).toBe("dark");
  fireEvent.change(selector, { target: { value: "light" } });
  expect(document.documentElement.dataset.theme).toBe("light");
  view.unmount();
  expect(listeners.size).toBe(0);
});
it("responds to other-tab changes and storage clearing", () => {
  render(<DisplaySettings />);
  act(() => {
    localStorage.setItem(INTERFACE_PREFERENCES_KEY, '{"navigation":"expanded"}');
    window.dispatchEvent(new StorageEvent("storage", { key: INTERFACE_PREFERENCES_KEY }));
  });
  expect(screen.getByRole("combobox", { name: /^Desktop sidebar/ })).toHaveValue("expanded");
  act(() => { localStorage.clear(); window.dispatchEvent(new StorageEvent("storage", { key: null })); });
  expect(screen.getByRole("combobox", { name: /^Desktop sidebar/ })).toHaveValue("compact");
});
it("shows a useful error when storage is blocked", () => {
  render(<DisplaySettings />);
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("denied"); });
  fireEvent.change(screen.getByRole("combobox", { name: /^Text size/ }), { target: { value: "large" } });
  expect(screen.getByRole("alert")).toHaveTextContent("could not save");
  expect(screen.getByRole("combobox", { name: /^Text size/ })).toHaveValue("standard");
});
