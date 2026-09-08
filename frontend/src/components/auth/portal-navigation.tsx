"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { usePortalAuth } from "./auth-provider";
import type { Portal } from "@/lib/auth/types";

const links: Record<Portal, readonly [string, string][]> = {
  CITIZEN: [["/citizen/dashboard", "Overview"], ["/citizen/doctors/search", "Find a doctor"], ["/citizen/appointments", "Appointments"], ["/citizen/profile", "My profile"]],
  PROFESSIONAL: [["/professional/dashboard", "My workspace"], ["/professional/chamber", "Chamber"], ["/professional/visits", "Consultations"], ["/professional/status", "Role status"]],
  ADMIN: [["/admin/dashboard", "Overview"], ["/admin/professional-registrations", "Verification queue"], ["/admin/facilities", "Facilities"], ["/admin/citizen-identities", "Citizen records"]],
};

function isActivePath(pathname: string, href: string): boolean {
  if (pathname === href || pathname.startsWith(`${href}/`)) return true;
  return href === "/citizen/doctors/search" && pathname.startsWith("/citizen/doctors/");
}

export function PortalNavigation({ portal }: { portal: Portal }) {
  const auth = usePortalAuth(portal);
  const pathname = usePathname();
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(false);
  if (auth.status !== "authenticated" || !auth.isRequiredPortal) return null;

  const signOut = async () => {
    setPending(true);
    setError(false);
    try {
      await auth.logout();
      router.replace(`/${portal.toLowerCase()}/login`);
    } catch {
      setError(true);
    } finally {
      setPending(false);
    }
  };

  return (
    <nav aria-label={`${portal.toLowerCase()} navigation`} className="mx-auto flex max-w-7xl flex-wrap items-center gap-1 px-5 pb-3 text-sm sm:px-8 lg:px-10">
      {links[portal].map(([href, label]) => <Link key={href} href={href} aria-current={isActivePath(pathname, href) ? "page" : undefined} className="inline-flex min-h-11 items-center rounded-lg px-3 font-semibold text-slate-600 hover:bg-slate-100 aria-[current=page]:bg-slate-900 aria-[current=page]:text-white">{label}</Link>)}
      <button className="ml-auto min-h-11 rounded-lg px-3 font-semibold text-slate-600 hover:bg-slate-100 disabled:opacity-50" type="button" disabled={pending} onClick={() => { if (window.confirm("Sign out of HealthLink? Save any unfinished work first.")) void signOut(); }}>{pending ? "Signing out…" : "Sign out"}</button>
      {error ? <p role="alert" className="w-full text-rose-700">We could not sign you out. Please try again.</p> : null}
    </nav>
  );
}
