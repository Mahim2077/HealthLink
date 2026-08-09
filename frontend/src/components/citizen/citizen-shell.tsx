import Link from "next/link";
import type { ReactNode } from "react";

import { HealthLinkMark } from "@/components/brand/healthlink-mark";

export function CitizenShell({ children }: { children: ReactNode }) {
  return (
    <div className="relative isolate flex min-h-screen flex-col overflow-hidden bg-[#f5faf8]">
      <div
        aria-hidden="true"
        className="absolute inset-x-0 top-0 -z-20 h-[34rem] bg-[radial-gradient(circle_at_15%_5%,rgba(45,212,191,0.18),transparent_30%),radial-gradient(circle_at_85%_8%,rgba(56,189,248,0.12),transparent_28%)]"
      />
      <div aria-hidden="true" className="page-grid absolute inset-x-0 top-0 -z-10 h-[32rem] opacity-60" />

      <header className="border-b border-white/70 bg-white/65 backdrop-blur-xl">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-5 py-4 sm:px-8 lg:px-10">
          <Link
            aria-label="HealthLink home"
            className="group inline-flex items-center gap-3 rounded-xl focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-teal-700"
            href="/"
          >
            <HealthLinkMark className="size-9 text-teal-700 shadow-md shadow-teal-900/10 transition group-hover:scale-[1.03]" />
            <span className="text-base font-bold tracking-[-0.025em] text-slate-950">
              Health<span className="text-teal-700">Link</span>
            </span>
          </Link>

          <div className="inline-flex items-center gap-2 rounded-full border border-teal-200 bg-white px-3 py-2 text-xs font-semibold text-teal-800 shadow-sm">
            <span className="flex size-5 items-center justify-center rounded-full bg-teal-100">
              <svg aria-hidden="true" className="size-3.5" fill="none" viewBox="0 0 20 20">
                <path
                  d="M10 10a3.2 3.2 0 1 0 0-6.4 3.2 3.2 0 0 0 0 6.4Zm5.5 6.4a5.5 5.5 0 0 0-11 0"
                  stroke="currentColor"
                  strokeLinecap="round"
                  strokeWidth="1.6"
                />
              </svg>
            </span>
            Citizen portal
          </div>
        </div>
      </header>

      {children}

      <footer className="border-t border-slate-200/80 bg-white/55">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-2 px-5 py-7 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between sm:px-8 lg:px-10">
          <p>HealthLink keeps care connected around one trusted identity.</p>
          <p>Your privacy is protected through trusted, role-aware access.</p>
        </div>
      </footer>
    </div>
  );
}
