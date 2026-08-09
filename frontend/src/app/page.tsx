import Link from "next/link";

import { HealthLinkMark } from "@/components/brand/healthlink-mark";

type PortalKind = "citizen" | "professional" | "admin";

const portalCards: Array<{
  kind: PortalKind;
  eyebrow: string;
  title: string;
  description: string;
  detail: string;
  accent: string;
}> = [
  {
    kind: "citizen",
    eyebrow: "Personal care",
    title: "Citizen Portal",
    description:
      "A clear home for identity, appointments, and a care story that stays with the person.",
    detail: "Designed around ownership and confidence",
    accent: "bg-teal-50 text-teal-700 ring-teal-100",
  },
  {
    kind: "professional",
    eyebrow: "Clinical context",
    title: "Professional Portal",
    description:
      "Focused tools shaped by a verified role and the patient who is currently receiving care.",
    detail: "Designed for safe, efficient consultations",
    accent: "bg-sky-50 text-sky-700 ring-sky-100",
  },
  {
    kind: "admin",
    eyebrow: "Trusted operations",
    title: "Admin Portal",
    description:
      "Purpose-built oversight for professional verification, facilities, and identity support.",
    detail: "Designed for accountable decisions",
    accent: "bg-indigo-50 text-indigo-700 ring-indigo-100",
  },
];

const principles = [
  {
    number: "01",
    title: "One connected identity",
    description:
      "Citizen and professional capabilities are designed around one person—not fragmented accounts.",
  },
  {
    number: "02",
    title: "Access follows context",
    description:
      "Portal, verified role, and patient relationship form the foundation for every protected action.",
  },
  {
    number: "03",
    title: "Calm by design",
    description:
      "Clear language, accessible states, and thoughtful hierarchy keep healthcare workflows understandable.",
  },
];

function ArrowIcon() {
  return (
    <svg aria-hidden="true" className="size-4" fill="none" viewBox="0 0 20 20">
      <path
        d="M4 10h12m-4.5-4.5L16 10l-4.5 4.5"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.7"
      />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg aria-hidden="true" className="size-4" fill="none" viewBox="0 0 20 20">
      <path
        d="m5.2 10.3 3 3 6.6-6.6"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2"
      />
    </svg>
  );
}

function PortalIcon({ kind }: { kind: PortalKind }) {
  if (kind === "citizen") {
    return (
      <svg aria-hidden="true" className="size-6" fill="none" viewBox="0 0 24 24">
        <path
          d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm7 8a7 7 0 0 0-14 0"
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="1.7"
        />
      </svg>
    );
  }

  if (kind === "professional") {
    return (
      <svg aria-hidden="true" className="size-6" fill="none" viewBox="0 0 24 24">
        <path
          d="M9 4h6v4H9V4Zm-3 3H4.8A1.8 1.8 0 0 0 3 8.8v9.4A1.8 1.8 0 0 0 4.8 20h14.4a1.8 1.8 0 0 0 1.8-1.8V8.8A1.8 1.8 0 0 0 19.2 7H18M9 14h6m-3-3v6"
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="1.7"
        />
      </svg>
    );
  }

  return (
    <svg aria-hidden="true" className="size-6" fill="none" viewBox="0 0 24 24">
      <path
        d="M12 3 5 6v5c0 4.7 2.8 8 7 10 4.2-2 7-5.3 7-10V6l-7-3Zm-3 9 2 2 4-4"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.7"
      />
    </svg>
  );
}

export default function Home() {
  return (
    <div className="relative isolate min-h-screen overflow-hidden bg-[#f7faf9]">
      <div aria-hidden="true" className="hero-glow absolute inset-0 -z-20" />
      <div aria-hidden="true" className="page-grid absolute inset-x-0 top-0 -z-10 h-[48rem]" />

      <header className="mx-auto flex w-full max-w-7xl items-center justify-between px-5 py-5 sm:px-8 lg:px-10">
        <a
          aria-label="HealthLink home"
          className="group inline-flex items-center gap-3 rounded-xl focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-teal-700"
          href="#main-content"
        >
          <HealthLinkMark className="size-10 text-teal-700 shadow-md shadow-teal-900/10 transition group-hover:scale-[1.03]" />
          <span className="text-lg font-bold tracking-[-0.025em] text-slate-950">
            Health<span className="text-teal-700">Link</span>
          </span>
        </a>

        <nav aria-label="Primary navigation" className="hidden items-center gap-7 md:flex">
          <a className="text-sm font-medium text-slate-600 transition hover:text-slate-950" href="#portals">
            Portals
          </a>
          <a className="text-sm font-medium text-slate-600 transition hover:text-slate-950" href="#principles">
            Principles
          </a>
          <a className="text-sm font-medium text-slate-600 transition hover:text-slate-950" href="#foundation">
            Foundation
          </a>
        </nav>

        <div className="inline-flex items-center gap-2 rounded-full border border-teal-200/80 bg-white/80 px-3 py-2 text-xs font-semibold text-teal-800 shadow-sm backdrop-blur">
          <span className="size-2 rounded-full bg-teal-500 shadow-[0_0_0_4px_rgba(20,184,166,0.12)]" />
          Citizen care connected
        </div>
      </header>

      <main id="main-content">
        <section className="mx-auto grid w-full max-w-7xl items-center gap-14 px-5 pb-24 pt-16 sm:px-8 sm:pt-24 lg:grid-cols-[1.03fr_0.97fr] lg:px-10 lg:pb-32 lg:pt-28">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white/85 px-3.5 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-600 shadow-sm backdrop-blur">
              <span className="flex size-5 items-center justify-center rounded-full bg-teal-100 text-teal-700">
                <CheckIcon />
              </span>
              Healthcare information, thoughtfully connected
            </div>

            <h1 className="mt-7 max-w-[13ch] font-display text-5xl font-bold leading-[1.02] tracking-[-0.055em] text-slate-950 sm:text-6xl lg:text-[4.6rem]">
              One health story, connected with care.
            </h1>
            <p className="mt-7 max-w-2xl text-lg leading-8 text-slate-600 sm:text-xl sm:leading-9">
              HealthLink keeps a citizen&apos;s healthcare journey coherent—while giving every portal the clarity and boundaries it needs.
            </p>

            <div className="mt-9 flex flex-col gap-3 sm:flex-row">
              <a
                className="inline-flex min-h-12 items-center justify-center gap-2 rounded-2xl bg-teal-700 px-6 text-sm font-semibold text-white shadow-lg shadow-teal-900/15 transition hover:-translate-y-0.5 hover:bg-teal-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700"
                href="#foundation"
              >
                Explore connected care
                <ArrowIcon />
              </a>
              <a
                className="inline-flex min-h-12 items-center justify-center rounded-2xl border border-slate-300 bg-white/75 px-6 text-sm font-semibold text-slate-800 shadow-sm backdrop-blur transition hover:-translate-y-0.5 hover:border-slate-400 hover:bg-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700"
                href="#portals"
              >
                See the portal model
              </a>
            </div>

            <dl className="mt-10 grid max-w-2xl grid-cols-3 gap-4 border-t border-slate-200/80 pt-7">
              <div>
                <dt className="text-xs font-medium uppercase tracking-[0.12em] text-slate-500">Identity</dt>
                <dd className="mt-1.5 text-sm font-semibold text-slate-900">One person</dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase tracking-[0.12em] text-slate-500">Experience</dt>
                <dd className="mt-1.5 text-sm font-semibold text-slate-900">Three portals</dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase tracking-[0.12em] text-slate-500">Privacy</dt>
                <dd className="mt-1.5 text-sm font-semibold text-slate-900">By context</dd>
              </div>
            </dl>
          </div>

          <div className="relative mx-auto w-full max-w-xl lg:mx-0 lg:ml-auto">
            <div aria-hidden="true" className="absolute -inset-8 -z-10 rounded-full bg-teal-200/20 blur-3xl" />
            <div className="soft-shadow overflow-hidden rounded-[2rem] border border-white/90 bg-white/90 p-3 backdrop-blur-xl">
              <div className="rounded-[1.45rem] bg-slate-950 p-6 text-white sm:p-8">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-teal-300">Product vision</p>
                    <h2 className="mt-2 text-2xl font-semibold tracking-tight">Care continuity</h2>
                  </div>
                  <span className="flex size-11 items-center justify-center rounded-2xl bg-white/10 text-teal-200 ring-1 ring-inset ring-white/10">
                    <svg aria-hidden="true" className="size-6" fill="none" viewBox="0 0 24 24">
                      <path
                        d="M12 21s8-4.4 8-11V5l-8-3-8 3v5c0 6.6 8 11 8 11Zm-3-9.5 2 2 4.5-4.5"
                        stroke="currentColor"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="1.7"
                      />
                    </svg>
                  </span>
                </div>

                <div className="mt-8 space-y-3">
                  {[
                    ["Identity", "A consistent starting point"],
                    ["Verified context", "The right role for each action"],
                    ["Care record", "Structured around real encounters"],
                  ].map(([label, description], index) => (
                    <div
                      className="flex items-center gap-4 rounded-2xl border border-white/10 bg-white/[0.055] p-4"
                      key={label}
                    >
                      <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-teal-400/15 text-sm font-bold text-teal-200">
                        {index + 1}
                      </span>
                      <div>
                        <p className="text-sm font-semibold text-white">{label}</p>
                        <p className="mt-0.5 text-xs leading-5 text-slate-400">{description}</p>
                      </div>
                      {index < 2 ? (
                        <span aria-hidden="true" className="ml-auto text-slate-600">→</span>
                      ) : (
                        <span className="ml-auto flex size-7 items-center justify-center rounded-full bg-teal-400/15 text-teal-200">
                          <CheckIcon />
                        </span>
                      )}
                    </div>
                  ))}
                </div>

                <div className="mt-5 flex items-center gap-3 rounded-2xl bg-teal-300 px-4 py-4 text-slate-950">
                  <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-slate-950 text-teal-200">
                    <svg aria-hidden="true" className="size-5" fill="none" viewBox="0 0 20 20">
                      <path
                        d="M10 2.5v15M2.5 10h15"
                        stroke="currentColor"
                        strokeLinecap="round"
                        strokeWidth="2.2"
                      />
                    </svg>
                  </span>
                  <div>
                    <p className="text-sm font-bold">Human-centered from the start</p>
                    <p className="mt-0.5 text-xs text-slate-800">Calm interfaces for high-trust moments.</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="absolute -bottom-7 -left-5 hidden items-center gap-3 rounded-2xl border border-white bg-white/95 p-3.5 shadow-xl shadow-slate-900/10 backdrop-blur sm:flex">
              <span className="flex size-10 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
                <CheckIcon />
              </span>
              <div>
                <p className="text-xs font-semibold text-slate-950">Accessible states</p>
                <p className="mt-0.5 text-[11px] text-slate-500">Clear at every step</p>
              </div>
            </div>
          </div>
        </section>

        <section className="border-y border-slate-200/80 bg-white/70 py-20 backdrop-blur-sm sm:py-24" id="portals">
          <div className="mx-auto w-full max-w-7xl px-5 sm:px-8 lg:px-10">
            <div className="max-w-2xl">
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-teal-700">Three focused experiences</p>
              <h2 className="mt-4 font-display text-3xl font-bold tracking-[-0.04em] text-slate-950 sm:text-4xl">
                One platform. Clear boundaries.
              </h2>
              <p className="mt-4 text-base leading-7 text-slate-600">
                Each portal is shaped for its responsibility while sharing one calm, consistent HealthLink design language.
              </p>
            </div>

            <div className="mt-12 grid gap-5 lg:grid-cols-3">
              {portalCards.map((portal) => (
                <article
                  className="group rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm transition duration-300 hover:-translate-y-1 hover:border-slate-300 hover:shadow-xl hover:shadow-slate-900/[0.06] sm:p-7"
                  key={portal.title}
                >
                  <div className="flex items-center justify-between gap-4">
                    <span className={"flex size-12 items-center justify-center rounded-2xl ring-1 ring-inset " + portal.accent}>
                      <PortalIcon kind={portal.kind} />
                    </span>
                    <span
                      className={
                        "rounded-full px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] " +
                        (portal.kind === "citizen"
                          ? "bg-emerald-50 text-emerald-700"
                          : portal.kind === "professional"
                            ? "bg-sky-50 text-sky-700"
                          : "bg-indigo-50 text-indigo-700")
                      }
                    >
                      {portal.kind === "citizen"
                        ? "Available now"
                        : portal.kind === "professional"
                          ? "Registration open"
                          : "Available now"}
                    </span>
                  </div>
                  <p className="mt-7 text-xs font-bold uppercase tracking-[0.16em] text-slate-500">{portal.eyebrow}</p>
                  <h3 className="mt-2 text-xl font-bold tracking-tight text-slate-950">{portal.title}</h3>
                  <p className="mt-3 text-sm leading-6 text-slate-600">{portal.description}</p>
                  {portal.kind === "citizen" ? (
                    <div className="mt-6 flex flex-wrap gap-2 border-t border-slate-100 pt-5">
                      <Link
                        className="inline-flex min-h-10 items-center justify-center rounded-xl bg-teal-700 px-4 text-xs font-bold text-white transition hover:bg-teal-800"
                        href="/citizen/login"
                      >
                        Citizen sign in
                      </Link>
                      <Link
                        className="inline-flex min-h-10 items-center justify-center rounded-xl border border-slate-300 px-4 text-xs font-bold text-slate-700 transition hover:border-slate-400"
                        href="/citizen/register"
                      >
                        Create account
                      </Link>
                    </div>
                  ) : portal.kind === "professional" ? (
                    <div className="mt-6 flex flex-wrap gap-2 border-t border-slate-100 pt-5">
                      <Link
                        className="inline-flex min-h-10 items-center justify-center rounded-xl bg-sky-700 px-4 text-xs font-bold text-white transition hover:bg-sky-800"
                        href="/professional/register"
                      >
                        Apply with NID
                      </Link>
                      <Link
                        className="inline-flex min-h-10 items-center justify-center rounded-xl border border-slate-300 px-4 text-xs font-bold text-slate-700 transition hover:border-slate-400"
                        href="/professional/onboard"
                      >
                        Existing citizen
                      </Link>
                    </div>
                  ) : (
                    <div className="mt-6 flex flex-wrap gap-2 border-t border-slate-100 pt-5">
                      <Link className="inline-flex min-h-10 items-center justify-center rounded-xl bg-indigo-700 px-4 text-xs font-bold text-white transition hover:bg-indigo-800" href="/admin/login">Admin sign in</Link>
                      <span className="inline-flex min-h-10 items-center text-xs font-semibold text-slate-500">Trusted accounts only</span>
                    </div>
                  )}
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto w-full max-w-7xl px-5 py-20 sm:px-8 sm:py-28 lg:px-10" id="principles">
          <div className="grid gap-12 lg:grid-cols-[0.72fr_1.28fr] lg:gap-20">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-teal-700">Design principles</p>
              <h2 className="mt-4 font-display text-3xl font-bold tracking-[-0.04em] text-slate-950 sm:text-4xl">
                Trust should feel visible.
              </h2>
              <p className="mt-5 text-base leading-7 text-slate-600">
                HealthLink brings clarity, consistency, and thoughtful safeguards to every care experience.
              </p>
            </div>

            <div className="divide-y divide-slate-200 border-y border-slate-200">
              {principles.map((principle) => (
                <article className="grid gap-3 py-7 sm:grid-cols-[4rem_1fr] sm:gap-5 sm:py-8" key={principle.number}>
                  <span className="font-mono text-xs font-semibold text-teal-700">{principle.number}</span>
                  <div>
                    <h3 className="text-lg font-bold tracking-tight text-slate-950">{principle.title}</h3>
                    <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">{principle.description}</p>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto w-full max-w-7xl px-5 pb-20 sm:px-8 sm:pb-28 lg:px-10" id="foundation">
          <div className="overflow-hidden rounded-[2rem] bg-teal-800 px-6 py-10 text-white shadow-2xl shadow-teal-950/15 sm:px-10 sm:py-12 lg:px-14">
            <div className="grid items-end gap-10 lg:grid-cols-[1fr_auto]">
              <div className="max-w-2xl">
                <p className="text-xs font-bold uppercase tracking-[0.18em] text-teal-200">Connected care foundation</p>
                <h2 className="mt-4 font-display text-3xl font-bold tracking-[-0.04em] sm:text-4xl">
                  Built for dependable care journeys.
                </h2>
                <p className="mt-4 text-base leading-7 text-teal-50/80">
                  A calm, responsive experience connects trusted identity with the right portal and the right level of access.
                </p>
              </div>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-2">
                {["Trusted identity", "Clear portals", "Private by context", "Accessible states"].map((item) => (
                  <span
                    className="flex min-h-11 items-center gap-2 rounded-xl bg-white/10 px-3.5 text-xs font-semibold ring-1 ring-inset ring-white/10"
                    key={item}
                  >
                    <CheckIcon />
                    {item}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200 bg-white/60">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-4 px-5 py-8 sm:flex-row sm:items-center sm:justify-between sm:px-8 lg:px-10">
          <div className="flex items-center gap-2.5">
            <HealthLinkMark className="size-8 text-teal-700" />
            <span className="text-sm font-bold text-slate-950">HealthLink</span>
          </div>
          <p className="text-xs leading-5 text-slate-500">Connected care, centered on people and protected by context.</p>
        </div>
      </footer>
    </div>
  );
}
