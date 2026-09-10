import { ShieldCheckIcon } from "@heroicons/react/24/outline";
import type { ReactNode } from "react";

export function CitizenAuthCard({
  children,
  description,
  eyebrow,
  title,
}: {
  children: ReactNode;
  description: string;
  eyebrow: string;
  title: string;
}) {
  return (
    <main className="mx-auto grid w-full max-w-7xl flex-1 items-start gap-8 px-5 py-10 sm:px-8 sm:py-14 lg:grid-cols-[0.75fr_1.25fr] lg:gap-12 lg:px-10 lg:py-16" id="main-content">
      <section className="order-2 max-w-lg pt-2 lg:order-1 lg:sticky lg:top-10 lg:pt-8">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-teal-700">{eyebrow}</p>
        <h1 className="mt-4 font-display text-4xl font-bold tracking-[-0.045em] text-slate-950 sm:text-5xl">
          {title}
        </h1>
        <p className="mt-5 text-base leading-7 text-slate-600 sm:text-lg">{description}</p>

        <div className="mt-7 rounded-xl border border-teal-100 bg-teal-50/80 p-5">
          <div className="flex gap-3">
            <span className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-full bg-white text-teal-700 shadow-sm">
              <ShieldCheckIcon aria-hidden="true" className="size-5" />
            </span>
            <div>
              <p className="text-sm font-bold text-teal-950">Protected by design</p>
              <p className="mt-1 text-xs leading-5 text-teal-900/70">
                Your identity supports secure account access and is handled with care at every step.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="order-1 rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_22px_60px_-42px_rgba(15,23,42,0.45)] sm:p-8 lg:order-2 lg:p-10">
        {children}
      </section>
    </main>
  );
}
