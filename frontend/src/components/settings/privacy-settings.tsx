"use client";

import Link from "next/link";
import { AccessHistoryPanel } from "@/components/privacy/access-history";

export function PrivacySettings() {
  return <div className="space-y-6">
    <section className="hl-settings-card" aria-labelledby="privacy-title">
      <h2 id="privacy-title" className="hl-section-title">Privacy & sharing</h2>
      <p className="hl-section-description">You control who can access your records. Review sharing regularly and revoke it when it is no longer needed.</p>
      <div className="hl-setting-row mt-4"><div><h3 className="font-semibold">Medical record sharing</h3><p className="hl-setting-help">Choose a verified doctor, select records, set an optional expiry or revoke a grant.</p></div><Link className="hl-button-secondary shrink-0" href="/citizen/access-grants">Manage access grants</Link></div>
      <div className="hl-setting-row border-t border-slate-100"><div><h3 className="font-semibold">AI conversations & record consent</h3><p className="hl-setting-help">Conversations are saved privately to your account. Open or delete them in the AI assistant. Records stay off unless you explicitly include them for a request.</p></div><Link className="hl-button-secondary shrink-0" href="/citizen/ai-assistant">Open AI assistant</Link></div>
      <p className="mt-4 rounded-xl bg-[var(--portal-soft)] p-4 text-sm leading-6 text-[var(--portal-strong)]">The AI explains medical information. It does not diagnose, prescribe or replace your doctor.</p>
    </section>
    <section className="hl-settings-card" aria-labelledby="access-history-title"><h2 id="access-history-title" className="hl-section-title">Privacy and access history</h2><p className="hl-section-description mb-6">Recorded access to your medical information, from the introduction of this feature. Times are shown in Dhaka time.</p><AccessHistoryPanel /></section>
  </div>;
}
