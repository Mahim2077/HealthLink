"use client";

import { useMemo, useSyncExternalStore } from "react";

export type InterfacePreferences = {
  textSize: "standard" | "large";
  motion: "system" | "reduced";
  navigation: "compact" | "expanded";
  theme: "light" | "dark" | "system";
};
export const DEFAULT_INTERFACE_PREFERENCES: InterfacePreferences = {
  textSize: "standard", motion: "system", navigation: "compact", theme: "light",
};
export const INTERFACE_PREFERENCES_KEY = "healthlink.interface.v1";
const changedEvent = "healthlink-interface-change";

export function parseInterfacePreferences(raw: string | null): InterfacePreferences {
  try {
    const value: unknown = JSON.parse(raw ?? "null");
    if (!value || typeof value !== "object") return DEFAULT_INTERFACE_PREFERENCES;
    const record = value as Record<string, unknown>;
    return {
      textSize: record.textSize === "large" ? "large" : "standard",
      motion: record.motion === "reduced" ? "reduced" : "system",
      navigation: record.navigation === "expanded" ? "expanded" : "compact",
      theme: record.theme === "dark" || record.theme === "system" ? record.theme : "light",
    };
  } catch { return DEFAULT_INTERFACE_PREFERENCES; }
}

function snapshot() {
  try { return window.localStorage.getItem(INTERFACE_PREFERENCES_KEY); }
  catch { return null; }
}

export function readInterfacePreferences(): InterfacePreferences {
  return parseInterfacePreferences(snapshot());
}
function subscribe(listener: () => void) {
  const onStorage = (event: StorageEvent) => {
    if (event.key === null || event.key === INTERFACE_PREFERENCES_KEY) listener();
  };
  window.addEventListener("storage", onStorage);
  window.addEventListener(changedEvent, listener);
  return () => {
    window.removeEventListener("storage", onStorage);
    window.removeEventListener(changedEvent, listener);
  };
}

/** Only allowlisted non-sensitive display choices are stored on this device. */
export function saveInterfacePreferences(value: InterfacePreferences): boolean {
  try {
    const safe = parseInterfacePreferences(JSON.stringify(value));
    window.localStorage.setItem(INTERFACE_PREFERENCES_KEY, JSON.stringify(safe));
    window.dispatchEvent(new Event(changedEvent));
    return true;
  } catch { return false; }
}
export function useInterfacePreferences(): InterfacePreferences {
  const raw = useSyncExternalStore(subscribe, snapshot, () => null);
  return useMemo(() => parseInterfacePreferences(raw), [raw]);
}
