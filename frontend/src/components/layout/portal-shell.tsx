"use client";

import {
  Bars3Icon,
  ChevronDownIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  EllipsisVerticalIcon,
  PlusIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import Link from "next/link";
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from "react";

import { usePortalAuth } from "@/components/auth/auth-provider";
import {
  PortalNavigation,
  PortalTextNavigation,
} from "@/components/auth/portal-navigation";
import { HealthLinkMark } from "@/components/brand/healthlink-mark";
import { loadAdminMe } from "@/lib/admin/api";
import type { Portal } from "@/lib/auth/types";
import { loadCitizenMe } from "@/lib/citizen/api";
import { loadProfessionalMe } from "@/lib/professional/api";

const MIN_SIDEBAR_WIDTH = 224;
const MAX_SIDEBAR_WIDTH = 340;
const COLLAPSED_SIDEBAR_WIDTH = 84;

const portalConfig: Record<
  Portal,
  {
    accountHref: string;
    accountLabel: string;
    background: string;
    eyebrow: string;
    footer: [string, string];
  }
> = {
  CITIZEN: {
    accountHref: "/citizen/profile",
    accountLabel: "Manage profile",
    background: "bg-[#f8fbfa]",
    eyebrow: "Citizen portal",
    footer: [
      "HealthLink keeps care connected around one trusted identity.",
      "Access follows the portal and role selected at sign in.",
    ],
  },
  PROFESSIONAL: {
    accountHref: "/professional/status",
    accountLabel: "Role details",
    background: "bg-[#f7fafc]",
    eyebrow: "Professional portal",
    footer: [
      "Professional access starts after role-specific verification.",
      "Each session uses one explicitly selected professional role.",
    ],
  },
  ADMIN: {
    accountHref: "/admin/dashboard",
    accountLabel: "Admin account",
    background: "bg-[#fafafd]",
    eyebrow: "Admin portal",
    footer: [
      "Trusted operational access only.",
      "Administrative actions are designed for accountable review.",
    ],
  },
};

function initials(value: string): string {
  const parts = value.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "HL";
  return parts.slice(0, 2).map((part) => part[0]).join("").toUpperCase();
}

function PortalAccount({ portal }: { portal: Portal }) {
  const auth = usePortalAuth(portal);
  const config = portalConfig[portal];
  const [displayName, setDisplayName] = useState("");

  useEffect(() => {
    if (auth.status !== "authenticated" || !auth.isRequiredPortal) return;
    let active = true;
    const request =
      portal === "CITIZEN"
        ? loadCitizenMe().then((record) => record.first_name + " " + record.last_name)
        : portal === "PROFESSIONAL"
          ? loadProfessionalMe().then((record) => record.first_name + " " + record.last_name)
          : loadAdminMe().then((record) => record.first_name + " " + record.last_name);

    void request.then(
      (name) => {
        if (active) setDisplayName(name.trim());
      },
      () => {
        if (active) setDisplayName("");
      },
    );
    return () => {
      active = false;
    };
  }, [auth.claims?.sub, auth.isRequiredPortal, auth.status, portal]);

  return (
    <Link
      className="group flex min-h-12 items-center gap-3 rounded-xl px-1.5 py-1 transition hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--portal-accent)] sm:px-2"
      href={config.accountHref}
    >
      <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-[var(--portal-soft)] text-sm font-bold text-[var(--portal-strongest)] ring-1 ring-inset ring-[var(--portal-border)]">
        {initials(displayName || config.eyebrow)}
      </span>
      <span className="hidden min-w-0 items-center text-left sm:flex">
        <span className="block max-w-44 truncate text-sm font-semibold text-slate-950">
          {displayName || "Your account"}
        </span>
        <span className="ml-4 block border-l border-slate-200 pl-4 text-xs font-semibold text-[var(--portal-accent)]">
          {config.accountLabel}
        </span>
      </span>
      <ChevronDownIcon
        aria-hidden="true"
        className="hidden size-4 text-slate-400 transition group-hover:translate-y-0.5 sm:block"
      />
    </Link>
  );
}

function PublicShell({ children, portal }: { children: ReactNode; portal: Portal }) {
  const config = portalConfig[portal];
  return (
    <div
      className={"relative isolate flex min-h-screen flex-col overflow-hidden " + config.background}
      data-portal={portal.toLowerCase()}
    >
      <header className="border-b border-slate-200/80 bg-white/90 backdrop-blur-xl">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-5 py-4 sm:px-8 lg:px-10">
          <Link
            aria-label="HealthLink home"
            className="inline-flex items-center gap-3 rounded-xl focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[var(--portal-accent)]"
            href="/"
          >
            <HealthLinkMark className="size-9 text-[var(--portal-accent)] shadow-sm" />
            <span className="text-base font-bold tracking-[-0.025em] text-slate-950">
              Health<span className="text-[var(--portal-accent)]">Link</span>
            </span>
          </Link>
          <span className="text-sm font-semibold text-[var(--portal-accent)]">{config.eyebrow}</span>
        </div>
      </header>
      {children}
      <footer className="mt-auto border-t border-slate-200/80 bg-white/75">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-2 px-5 py-6 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between sm:px-8 lg:px-10">
          <p>{config.footer[0]}</p>
          <p>{config.footer[1]}</p>
        </div>
      </footer>
    </div>
  );
}

export function PortalShell({ children, portal }: { children: ReactNode; portal: Portal }) {
  const auth = usePortalAuth(portal);
  const config = portalConfig[portal];
  const [collapsed, setCollapsed] = useState(true);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(260);
  const dragOrigin = useRef<{ pointerX: number; width: number } | null>(null);
  const authenticated = auth.status === "authenticated" && auth.isRequiredPortal;

  useEffect(() => {
    if (!mobileOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMobileOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [mobileOpen]);

  const stopResizing = useCallback(() => {
    dragOrigin.current = null;
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  }, []);

  useEffect(() => {
    const handlePointerMove = (event: PointerEvent) => {
      if (!dragOrigin.current) return;
      const nextWidth = Math.min(
        MAX_SIDEBAR_WIDTH,
        Math.max(
          MIN_SIDEBAR_WIDTH,
          dragOrigin.current.width + event.clientX - dragOrigin.current.pointerX,
        ),
      );
      setSidebarWidth(nextWidth);
    };
    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", stopResizing);
    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", stopResizing);
      stopResizing();
    };
  }, [stopResizing]);

  if (!authenticated) {
    return <PublicShell portal={portal}>{children}</PublicShell>;
  }

  const renderedWidth = collapsed ? COLLAPSED_SIDEBAR_WIDTH : sidebarWidth;
  const startResizing = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (collapsed) return;
    dragOrigin.current = { pointerX: event.clientX, width: sidebarWidth };
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    event.currentTarget.setPointerCapture(event.pointerId);
  };
  const adjustSidebar = (direction: number) => {
    if (collapsed) setCollapsed(false);
    setSidebarWidth((value) =>
      Math.min(MAX_SIDEBAR_WIDTH, Math.max(MIN_SIDEBAR_WIDTH, value + direction)),
    );
  };

  return (
    <div className={"min-h-screen " + config.background} data-portal={portal.toLowerCase()}>
      <div className="flex min-h-screen">
        <aside
          aria-label={config.eyebrow + " sidebar"}
          className="relative z-40 hidden h-screen shrink-0 flex-col overflow-visible bg-[var(--portal-sidebar)] text-white shadow-[14px_0_40px_-32px_rgba(15,23,42,0.7)] transition-[width] duration-200 lg:sticky lg:top-0 lg:flex"
          style={{ width: renderedWidth } as CSSProperties}
        >
          <div
            className={
              "flex min-h-24 items-center " +
              (collapsed ? "justify-center px-3" : "gap-3 px-5")
            }
          >
            <Link
              aria-label="HealthLink home"
              className="flex size-11 items-center justify-center rounded-xl bg-white text-[var(--portal-sidebar)] shadow-lg shadow-slate-950/25 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-white"
              href="/"
            >
              <PlusIcon aria-hidden="true" className="size-8 stroke-[2.25]" />
            </Link>
            {collapsed ? null : (
              <span className="truncate text-lg font-bold tracking-[-0.03em]">HealthLink</span>
            )}
          </div>

          <PortalNavigation collapsed={collapsed} portal={portal} />

          <button
            aria-label={collapsed ? "Expand navigation" : "Collapse navigation"}
            aria-expanded={!collapsed}
            className="absolute -right-4 top-8 z-20 flex size-9 items-center justify-center rounded-full border border-white/15 bg-[var(--portal-control)] text-white shadow-lg shadow-slate-950/20 transition hover:bg-[var(--portal-control-hover)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--portal-soft)]"
            onClick={() => setCollapsed((value) => !value)}
            title={collapsed ? "Expand navigation" : "Collapse navigation"}
            type="button"
          >
            {collapsed ? (
              <ChevronRightIcon aria-hidden="true" className="size-5" />
            ) : (
              <ChevronLeftIcon aria-hidden="true" className="size-5" />
            )}
          </button>

          <div
            aria-label="Resize navigation"
            aria-orientation="vertical"
            aria-valuemax={MAX_SIDEBAR_WIDTH}
            aria-valuemin={MIN_SIDEBAR_WIDTH}
            aria-valuenow={sidebarWidth}
            className={
              "absolute inset-y-0 -right-1 z-10 w-2 " +
              (collapsed ? "cursor-default" : "cursor-col-resize")
            }
            onKeyDown={(event) => {
              if (event.key === "ArrowLeft") adjustSidebar(-16);
              if (event.key === "ArrowRight") adjustSidebar(16);
              if (event.key === "Home") setSidebarWidth(MIN_SIDEBAR_WIDTH);
              if (event.key === "End") setSidebarWidth(MAX_SIDEBAR_WIDTH);
            }}
            onPointerDown={startResizing}
            role="separator"
            tabIndex={collapsed ? -1 : 0}
          >
            <span className="pointer-events-none absolute left-1/2 top-1/2 flex h-12 w-4 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-white/25 bg-[var(--portal-control)] text-white/85 shadow-sm">
              <EllipsisVerticalIcon aria-hidden="true" className="size-4" />
            </span>
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-30 border-b border-slate-200/90 bg-white/94 backdrop-blur-xl">
            <div className="flex min-h-20 items-center justify-between gap-4 px-5 sm:px-8 lg:px-10">
              <div className="flex min-w-0 items-center gap-3">
                <button
                  aria-expanded={mobileOpen}
                  aria-label="Open navigation"
                  className="flex size-11 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-700 shadow-sm lg:hidden"
                  onClick={() => setMobileOpen(true)}
                  type="button"
                >
                  <Bars3Icon aria-hidden="true" className="size-6" />
                </button>
                <span className="truncate text-base font-bold tracking-[-0.025em] text-[var(--portal-strong)] sm:text-lg">
                  {config.eyebrow}
                </span>
              </div>
              <PortalAccount portal={portal} />
            </div>
            <PortalTextNavigation portal={portal} />
          </header>

          <div className="flex min-h-0 flex-1 flex-col">{children}</div>

        </div>
      </div>

      {mobileOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            aria-label="Close navigation"
            className="absolute inset-0 bg-slate-950/45 backdrop-blur-[2px]"
            onClick={() => setMobileOpen(false)}
            type="button"
          />
          <aside
            aria-label={config.eyebrow + " navigation"}
            aria-modal="true"
            className="relative flex h-full w-[min(20rem,calc(100vw-2rem))] flex-col bg-[var(--portal-sidebar)] text-white shadow-2xl"
            role="dialog"
          >
            <div className="flex min-h-20 items-center justify-between gap-3 px-5">
              <Link
                className="flex items-center gap-3 rounded-xl"
                href="/"
                onClick={() => setMobileOpen(false)}
              >
                <span className="flex size-10 items-center justify-center rounded-xl bg-white text-[var(--portal-sidebar)] shadow-sm">
                  <PlusIcon aria-hidden="true" className="size-7 stroke-[2.25]" />
                </span>
                <span className="text-lg font-bold">HealthLink</span>
              </Link>
              <button
                aria-label="Close navigation"
                className="flex size-10 items-center justify-center rounded-xl bg-white/10"
                onClick={() => setMobileOpen(false)}
                type="button"
              >
                <XMarkIcon aria-hidden="true" className="size-6" />
              </button>
            </div>
            <PortalNavigation onNavigate={() => setMobileOpen(false)} portal={portal} />
          </aside>
        </div>
      ) : null}
    </div>
  );
}
