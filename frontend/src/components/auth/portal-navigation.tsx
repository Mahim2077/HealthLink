"use client";

import {
  ArrowRightStartOnRectangleIcon,
  BuildingOffice2Icon,
  CalendarDaysIcon,
  ChatBubbleBottomCenterTextIcon,
  ClipboardDocumentCheckIcon,
  HomeIcon,
  IdentificationIcon,
  MagnifyingGlassIcon,
  QueueListIcon,
  ShieldCheckIcon,
  UserCircleIcon,
} from "@heroicons/react/24/outline";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, type ComponentType, type SVGProps } from "react";

import { usePortalAuth } from "./auth-provider";
import type { Portal } from "@/lib/auth/types";

type NavigationItem = {
  href: string;
  label: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
};

const links: Record<Portal, NavigationItem[]> = {
  CITIZEN: [
    { href: "/citizen/dashboard", icon: HomeIcon, label: "Overview" },
    { href: "/citizen/doctors/search", icon: MagnifyingGlassIcon, label: "Find a doctor" },
    { href: "/citizen/appointments", icon: CalendarDaysIcon, label: "Appointments" },
    { href: "/citizen/profile", icon: UserCircleIcon, label: "My profile" },
  ],
  PROFESSIONAL: [
    { href: "/professional/dashboard", icon: HomeIcon, label: "My workspace" },
    { href: "/professional/chamber", icon: QueueListIcon, label: "Chamber" },
    { href: "/professional/visits", icon: ChatBubbleBottomCenterTextIcon, label: "Consultations" },
    { href: "/professional/status", icon: ClipboardDocumentCheckIcon, label: "Role status" },
  ],
  ADMIN: [
    { href: "/admin/dashboard", icon: HomeIcon, label: "Overview" },
    { href: "/admin/professional-registrations", icon: ShieldCheckIcon, label: "Verification queue" },
    { href: "/admin/facilities", icon: BuildingOffice2Icon, label: "Facilities" },
    { href: "/admin/citizen-identities", icon: IdentificationIcon, label: "Citizen records" },
  ],
};

function isActivePath(pathname: string, href: string): boolean {
  if (pathname === href || pathname.startsWith(`${href}/`)) return true;
  return href === "/citizen/doctors/search" && pathname.startsWith("/citizen/doctors/");
}

export function PortalTextNavigation({ portal }: { portal: Portal }) {
  const pathname = usePathname();

  return (
    <nav
      aria-label={`${portal.toLowerCase()} page navigation`}
      className="hidden min-h-14 items-stretch overflow-x-auto border-t border-slate-100 px-5 sm:px-8 lg:flex lg:px-10"
    >
      <div className="flex min-w-max items-stretch gap-7">
        {links[portal].map(({ href, label }) => {
          const active = isActivePath(pathname, href);
          return (
            <Link
              aria-current={active ? "page" : undefined}
              className={`relative inline-flex min-h-14 items-center whitespace-nowrap text-sm font-semibold transition focus-visible:outline-2 focus-visible:outline-offset-[-4px] focus-visible:outline-teal-700 ${
                active
                  ? "text-teal-800 after:absolute after:inset-x-0 after:bottom-0 after:h-0.5 after:rounded-full after:bg-teal-700"
                  : "text-slate-600 hover:text-teal-800"
              }`}
              href={href}
              key={href}
            >
              {label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

export function PortalNavigation({
  collapsed = false,
  onNavigate,
  portal,
}: {
  collapsed?: boolean;
  onNavigate?: () => void;
  portal: Portal;
}) {
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
      onNavigate?.();
    } catch {
      setError(true);
    } finally {
      setPending(false);
    }
  };

  return (
    <nav
      aria-label={`${portal.toLowerCase()} navigation`}
      className="flex min-h-0 flex-1 flex-col px-3 pb-5"
    >
      <div className="space-y-1.5">
        {links[portal].map(({ href, icon: Icon, label }) => {
          const active = isActivePath(pathname, href);
          return (
            <Link
              aria-current={active ? "page" : undefined}
              aria-label={collapsed ? label : undefined}
              className={`group flex min-h-12 items-center rounded-xl text-sm font-semibold transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white ${
                collapsed ? "justify-center px-2" : "gap-3 px-3.5"
              } ${
                active
                  ? "bg-white/14 text-white shadow-sm ring-1 ring-inset ring-white/10"
                  : "text-white/68 hover:bg-white/8 hover:text-white"
              }`}
              href={href}
              key={href}
              onClick={onNavigate}
              title={collapsed ? label : undefined}
            >
              <Icon aria-hidden="true" className="size-5 shrink-0 stroke-[1.8]" />
              <span className={collapsed ? "sr-only" : "truncate"}>{label}</span>
            </Link>
          );
        })}
      </div>

      <div className="mt-auto border-t border-white/16 pt-4">
        <button
          aria-label={collapsed ? (pending ? "Signing out" : "Sign out") : undefined}
          className={`flex min-h-12 w-full items-center rounded-xl text-sm font-semibold text-white/70 transition hover:bg-white/8 hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white disabled:cursor-wait disabled:opacity-50 ${
            collapsed ? "justify-center px-2" : "gap-3 px-3.5"
          }`}
          disabled={pending}
          onClick={() => {
            if (window.confirm("Sign out of HealthLink? Save any unfinished work first.")) {
              void signOut();
            }
          }}
          title={collapsed ? "Sign out" : undefined}
          type="button"
        >
          <ArrowRightStartOnRectangleIcon aria-hidden="true" className="size-5 shrink-0 stroke-[1.8]" />
          <span className={collapsed ? "sr-only" : "truncate"}>{pending ? "Signing out…" : "Sign out"}</span>
        </button>
        {error ? (
          <p className={`mt-2 text-xs leading-5 text-rose-100 ${collapsed ? "sr-only" : "px-3"}`} role="alert">
            We could not sign you out. Please try again.
          </p>
        ) : null}
      </div>
    </nav>
  );
}
