"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { usePortalAuth } from "@/components/auth/auth-provider";
import { useSettingsContext } from "./settings-layout";

export function SecuritySettings() {
  const { portal, professional } = useSettingsContext();
  const auth = usePortalAuth(portal);
  const router = useRouter();
  const busy = useRef(false);
  const [pending, setPending] = useState<"current" | "all" | null>(null);
  const [error, setError] = useState("");
  const signOut = async (scope: "current" | "all") => {
    if (busy.current) return;
    const message = scope === "all" ? "Sign out all sessions for this HealthLink account, including this one and sessions in other portals? Save any unfinished work first." : "Sign out of this HealthLink session? Save any unfinished work first.";
    if (!window.confirm(message)) return;
    busy.current = true; setPending(scope); setError("");
    try {
      await (scope === "all" ? auth.logoutAll() : auth.logout());
      router.replace(`/${portal.toLowerCase()}/login`);
    } catch { setError("We could not sign you out. Please try again."); }
    finally { busy.current = false; setPending(null); }
  };
  return <div className="space-y-6">
    <section className="hl-settings-card" aria-labelledby="security-title">
      <h2 id="security-title" className="hl-section-title">Security & sessions</h2>
      <p className="hl-section-description">Control where your account stays signed in. Always sign out on shared devices.</p>
      <div className="mt-6 flex flex-wrap items-center justify-between gap-4 rounded-xl border border-[var(--portal-border)] bg-[var(--portal-soft)] p-4">
        <div><p className="text-sm font-semibold">This session</p><p className="mt-1 text-sm text-slate-600">{portal === "CITIZEN" ? "Citizen portal" : portal === "ADMIN" ? "Admin portal" : `Professional portal · ${professional?.role_name ?? "Selected role"}`}</p></div>
        <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-emerald-800 ring-1 ring-inset ring-emerald-200">Signed in</span>
      </div>
      <div className="hl-setting-row mt-2"><div><h3 className="font-semibold">Sign out on this device</h3><p className="hl-setting-help">End this session and return to the sign-in page.</p></div><button className="hl-button-secondary shrink-0" disabled={pending !== null} onClick={() => void signOut("current")} type="button">{pending === "current" ? "Signing out…" : "Sign out"}</button></div>
      <div className="hl-setting-row border-t border-slate-100"><div><h3 className="font-semibold">Sign out everywhere</h3><p className="hl-setting-help">Revoke all sessions for this account across devices and portals, including this session.</p></div><button className="hl-button-secondary hl-button-danger shrink-0" disabled={pending !== null} onClick={() => void signOut("all")} type="button">{pending === "all" ? "Signing out everywhere…" : "Sign out all sessions"}</button></div>
      {error ? <p role="alert" className="mt-4 text-sm text-rose-800">{error}</p> : null}
    </section>
    <aside className="rounded-xl border border-slate-200 bg-white px-5 py-4 text-sm leading-6 text-slate-600">Password changes and two-factor authentication are not available in HealthLink yet. Never share your password or medical records with untrusted people.</aside>
  </div>;
}
