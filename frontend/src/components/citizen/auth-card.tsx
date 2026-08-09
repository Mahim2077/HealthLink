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
    <main className="mx-auto grid w-full max-w-7xl flex-1 items-start gap-10 px-5 py-12 sm:px-8 sm:py-16 lg:grid-cols-[0.75fr_1.25fr] lg:px-10 lg:py-20" id="main-content">
      <section className="max-w-lg pt-2 lg:sticky lg:top-10 lg:pt-10">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-teal-700">{eyebrow}</p>
        <h1 className="mt-4 font-display text-4xl font-bold tracking-[-0.045em] text-slate-950 sm:text-5xl">
          {title}
        </h1>
        <p className="mt-5 text-base leading-7 text-slate-600 sm:text-lg">{description}</p>

        <div className="mt-8 rounded-2xl border border-teal-100 bg-teal-50/80 p-5">
          <div className="flex gap-3">
            <span className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-xl bg-white text-teal-700 shadow-sm">
              <svg aria-hidden="true" className="size-5" fill="none" viewBox="0 0 20 20">
                <path
                  d="M10 2.5 4 5v4.3c0 4 2.4 6.8 6 8.2 3.6-1.4 6-4.2 6-8.2V5l-6-2.5Zm-2.4 7.4 1.6 1.6 3.4-3.4"
                  stroke="currentColor"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="1.6"
                />
              </svg>
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

      <section className="soft-shadow rounded-[2rem] border border-white bg-white/95 p-5 backdrop-blur sm:p-8 lg:p-10">
        {children}
      </section>
    </main>
  );
}
