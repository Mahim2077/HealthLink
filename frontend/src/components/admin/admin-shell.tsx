import Link from "next/link";
import type { ReactNode } from "react";

import { HealthLinkMark } from "@/components/brand/healthlink-mark";

export function AdminShell({ children }: { children: ReactNode }) {
  return (
    <div className="relative isolate flex min-h-screen flex-col overflow-hidden bg-[#f7f7fc]">
      <div aria-hidden="true" className="absolute inset-x-0 top-0 -z-20 h-[36rem] bg-[radial-gradient(circle_at_15%_5%,rgba(99,102,241,0.16),transparent_30%),radial-gradient(circle_at_85%_8%,rgba(139,92,246,0.10),transparent_28%)]" />
      <div aria-hidden="true" className="page-grid absolute inset-x-0 top-0 -z-10 h-[32rem] opacity-45" />
      <header className="border-b border-white/70 bg-white/70 backdrop-blur-xl">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-5 py-4 sm:px-8 lg:px-10">
          <Link aria-label="HealthLink home" className="inline-flex items-center gap-3 rounded-xl focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-indigo-700" href="/">
            <HealthLinkMark className="size-9 text-indigo-700 shadow-md shadow-indigo-900/10" />
            <span className="text-base font-bold tracking-[-0.025em] text-slate-950">Health<span className="text-indigo-700">Link</span></span>
          </Link>
          <div className="inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-white px-3 py-2 text-xs font-semibold text-indigo-800 shadow-sm">
            <span className="size-2 rounded-full bg-indigo-500" /> Admin portal
          </div>
        </div>
      </header>
      {children}
      <footer className="border-t border-slate-200/80 bg-white/55">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-2 px-5 py-7 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between sm:px-8 lg:px-10">
          <p>Trusted operational access only.</p><p>Administrative actions are designed for accountable review.</p>
        </div>
      </footer>
    </div>
  );
}
