"use client";

import { useEffect, useState } from "react";
import { DEFAULT_INTERFACE_PREFERENCES, readInterfacePreferences, saveInterfacePreferences, useInterfacePreferences, type InterfacePreferences } from "@/lib/settings/interface-preferences";

export function InterfacePreferencesBridge() {
  const preferences = useInterfacePreferences();
  useEffect(() => {
    document.documentElement.dataset.textSize = preferences.textSize;
    document.documentElement.dataset.motion = preferences.motion;
  }, [preferences]);
  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      // Read the actual browser snapshot even during the first hydration effect;
      // do not overwrite the bootstrap's saved theme with the server default.
      const choice = readInterfacePreferences().theme;
      document.documentElement.dataset.theme = choice === "system" ? (media.matches ? "dark" : "light") : choice;
    };
    apply();
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, [preferences.theme]);
  return null;
}

export function DisplaySettings() {
  const preferences = useInterfacePreferences();
  const [notice, setNotice] = useState<{ ok: boolean; text: string } | null>(null);
  const save = (value: InterfacePreferences) => {
    const ok = saveInterfacePreferences(value);
    setNotice({ ok, text: ok ? "Display preferences saved on this device." : "This browser could not save preferences. Check its storage settings and try again." });
  };
  return <section className="hl-settings-card" aria-labelledby="display-title">
    <h2 id="display-title" className="hl-section-title">Display & accessibility</h2>
    <p className="hl-section-description">Make HealthLink comfortable for you. These choices apply only to this browser, including other accounts using it.</p>
    <div className="mt-6 divide-y divide-slate-100">
      <label className="hl-setting-row" htmlFor="settings-theme">
        <span><span className="block font-semibold">Color theme</span><span className="hl-setting-help">Choose light or dark, or follow your device’s appearance.</span></span>
        <select id="settings-theme" className="hl-settings-select" value={preferences.theme} onChange={e => save({ ...preferences, theme: e.target.value as InterfacePreferences["theme"] })}>
          <option value="light">Light</option><option value="dark">Dark</option><option value="system">Use system setting</option>
        </select>
      </label>
      <label className="hl-setting-row" htmlFor="settings-text-size">
        <span><span className="block font-semibold">Text size</span><span className="hl-setting-help">Larger text keeps the same information and controls.</span></span>
        <select id="settings-text-size" className="hl-settings-select" value={preferences.textSize} onChange={e => save({ ...preferences, textSize: e.target.value as InterfacePreferences["textSize"] })}>
          <option value="standard">Standard</option><option value="large">Larger</option>
        </select>
      </label>
      <label className="hl-setting-row" htmlFor="settings-motion">
        <span><span className="block font-semibold">Motion</span><span className="hl-setting-help">System follows your device’s reduced-motion preference.</span></span>
        <select id="settings-motion" className="hl-settings-select" value={preferences.motion} onChange={e => save({ ...preferences, motion: e.target.value as InterfacePreferences["motion"] })}>
          <option value="system">Use system setting</option><option value="reduced">Reduce motion</option>
        </select>
      </label>
      <label className="hl-setting-row" htmlFor="settings-navigation">
        <span><span className="block font-semibold">Desktop sidebar</span><span className="hl-setting-help">Choose the default for a newly opened portal. You can still expand or collapse it anytime.</span></span>
        <select id="settings-navigation" className="hl-settings-select" value={preferences.navigation} onChange={e => save({ ...preferences, navigation: e.target.value as InterfacePreferences["navigation"] })}>
          <option value="compact">Compact icons</option><option value="expanded">Icons and labels</option>
        </select>
      </label>
    </div>
    <div className="mt-6 flex flex-wrap items-center gap-4 border-t border-slate-100 pt-5">
      <button className="hl-button-secondary" onClick={() => save(DEFAULT_INTERFACE_PREFERENCES)} type="button">Reset display preferences</button>
      <p className="text-xs leading-5 text-slate-500">No identity or medical information is stored with these choices.</p>
    </div>
    {notice ? <p className={"mt-4 text-sm " + (notice.ok ? "text-emerald-800" : "text-rose-800")} role={notice.ok ? "status" : "alert"}>{notice.text}</p> : null}
  </section>;
}
