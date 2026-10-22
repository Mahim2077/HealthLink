"use client";

import { CalendarDaysIcon, Cog6ToothIcon, ShieldCheckIcon, SwatchIcon, UserCircleIcon } from "@heroicons/react/24/outline";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { usePortalAuth } from "@/components/auth/auth-provider";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/async-state";
import { loadAdminMe } from "@/lib/admin/api";
import type { AdminMe } from "@/lib/admin/types";
import type { Portal } from "@/lib/auth/types";
import { loadProfessionalMe } from "@/lib/professional/api";
import type { ProfessionalMe } from "@/lib/professional/types";

type SettingsContextValue = { portal: Portal; professional: ProfessionalMe | null; admin: AdminMe | null };
const SettingsContext = createContext<SettingsContextValue | null>(null);
export function useSettingsContext() {
  const context = useContext(SettingsContext);
  if (!context) throw new Error("Settings content requires SettingsLayout.");
  return context;
}

function SettingsContent({ portal, children }: { portal: Portal; children: ReactNode }) {
  const pathname = usePathname();
  const [data, setData] = useState<SettingsContextValue | null>(null);
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0);
  useEffect(() => {
    let active = true;
    const load = async (): Promise<SettingsContextValue> => ({
      portal,
      professional: portal === "PROFESSIONAL" ? await loadProfessionalMe() : null,
      admin: portal === "ADMIN" ? await loadAdminMe() : null,
    });
    void load().then(value => { if (active) setData(value); }, () => {
      if (active) setError("We could not load your account settings. Please try again.");
    });
    return () => { active = false; };
  }, [portal, version]);
  const base = `/${portal.toLowerCase()}/settings`;
  const sections = [
    { href: base, label: "Account", description: "Profile & identity", icon: UserCircleIcon },
    { href: base + "/security", label: "Security", description: "Sign-in sessions", icon: ShieldCheckIcon },
    { href: base + "/appearance", label: "Display & accessibility", description: "Text, motion & navigation", icon: SwatchIcon },
    ...(portal === "CITIZEN" ? [{ href: base + "/privacy", label: "Privacy & sharing", description: "Records & access history", icon: ShieldCheckIcon }] : []),
    ...(data?.professional?.role_code === "DOCTOR" && data.professional.verification_status === "VERIFIED" ? [{ href: base + "/practice", label: "Practice hours", description: "Weekly availability", icon: CalendarDaysIcon }] : []),
  ];
  return <main id="main-content" className="hl-page hl-settings-page">
    <header className="hl-page-header flex items-start gap-4">
      <span className="hidden size-12 shrink-0 items-center justify-center rounded-2xl bg-[var(--portal-soft)] text-[var(--portal-accent)] ring-1 ring-inset ring-[var(--portal-border)] sm:flex"><Cog6ToothIcon className="size-6" aria-hidden="true" /></span>
      <div><h1 className="font-display text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">Settings</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">Your account, your preferences. Keep everyday care in your workspace.</p></div>
    </header>
    {error ? <ErrorState title="Settings unavailable" message={error} onAction={() => { setError(""); setVersion(v => v + 1); }} /> : !data ? <LoadingState label="Loading settings" /> :
      <div className="mt-5 grid items-start gap-5 sm:mt-7 sm:gap-6 xl:grid-cols-[14rem_minmax(0,1fr)] xl:gap-8">
        <nav aria-label="Settings sections" className="grid grid-cols-2 gap-2 xl:sticky xl:top-40 xl:grid-cols-1">
          {sections.map(({ href, label, description, icon: Icon }) => <Link key={href} href={href} aria-current={pathname === href ? "page" : undefined}
            className={"flex min-h-14 items-start gap-3 rounded-xl border px-3 py-3 text-sm transition " + (pathname === href ? "border-[var(--portal-border)] bg-[var(--portal-soft)] text-[var(--portal-strong)]" : "border-transparent text-slate-600 hover:bg-white hover:text-slate-950")}>
            <Icon className="mt-0.5 size-5 shrink-0" aria-hidden="true" /><span className="min-w-0"><span className="block font-semibold">{label}</span><span className="mt-1 hidden text-xs leading-5 text-slate-500 sm:block">{description}</span></span>
          </Link>)}
        </nav>
        <SettingsContext.Provider value={data}><div className="min-w-0 space-y-6">{children}</div></SettingsContext.Provider>
      </div>}
  </main>;
}

export function SettingsLayout({ portal, children }: { portal: Portal; children: ReactNode }) {
  const auth = usePortalAuth(portal);
  const { status, refreshSession } = auth;
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    if (status === "authenticated") return;
    let active = true;
    void refreshSession().catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [status, refreshSession]);
  if (status !== "authenticated") return <main id="main-content" className="hl-page">{failed ?
    <EmptyState title="Sign in to manage settings" message="Your account settings require a secure portal session." action={<Link className="hl-button-primary" href={`/${portal.toLowerCase()}/login`}>Sign in</Link>} /> : <LoadingState label="Checking your session" />}</main>;
  if (!auth.isRequiredPortal) return <main id="main-content" className="hl-page"><EmptyState title="Portal access required" message="This session belongs to another HealthLink portal." action={<Link href="/">Return to HealthLink</Link>} /></main>;
  return <SettingsContent key={`${portal}:${auth.claims?.sid}`} portal={portal}>{children}</SettingsContent>;
}
