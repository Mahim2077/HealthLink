import {
  ChevronDownIcon,
  DocumentTextIcon,
  MagnifyingGlassIcon,
  UserIcon,
} from "@heroicons/react/24/outline";
import Image from "next/image";
import Link from "next/link";

import { HealthLinkMark } from "@/components/brand/healthlink-mark";

const careSteps = [
  {
    description: "Set up one secure health identity.",
    icon: UserIcon,
    number: "1",
    title: "Create your profile",
  },
  {
    description: "Choose a trusted healthcare professional.",
    icon: MagnifyingGlassIcon,
    number: "2",
    title: "Find verified care",
  },
  {
    description: "Keep appointments and records together.",
    icon: DocumentTextIcon,
    number: "3",
    title: "Stay connected",
  },
];

const carePrinciples = [
  {
    description:
      "Straightforward language helps every person understand what comes next.",
    number: "01",
    title: "Clear by default",
  },
  {
    description:
      "Calm, considerate experiences support confidence in important moments.",
    number: "02",
    title: "Respectful at every step",
  },
  {
    description:
      "A familiar structure helps people stay oriented throughout their journey.",
    number: "03",
    title: "Consistent across care",
  },
];

const navigationLinkClass =
  "rounded-lg px-2 py-2 text-sm font-semibold text-indigo-950/75 transition hover:text-teal-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700";

export default function Home() {
  return (
    <div className="min-h-screen bg-white text-slate-950">
      <header className="border-b border-slate-200/80 bg-white">
        <div className="relative flex min-h-24 w-full flex-wrap items-center justify-between gap-x-4 px-5 py-4 sm:gap-x-8 sm:px-8 lg:px-[clamp(3rem,7.75vw,7rem)]">
          <Link
            aria-label="HealthLink home"
            className="group inline-flex items-center gap-3 rounded-xl focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-teal-700"
            href="/"
          >
            <HealthLinkMark className="size-11 text-teal-700 shadow-sm transition group-hover:scale-[1.02] sm:size-12" />
            <span className="text-xl font-extrabold tracking-[-0.035em] text-slate-950 sm:text-2xl">
              Health<span className="text-teal-700">Link</span>
            </span>
          </Link>

          <nav
            aria-label="Primary navigation"
            className="absolute left-1/2 hidden -translate-x-1/2 items-center gap-7 md:flex"
          >
            <a className={navigationLinkClass} href="#how-it-works">
              How it works
            </a>
            <Link className={navigationLinkClass} href="/professional/register">
              For professionals
            </Link>
          </nav>

          <details className="group relative z-20">
            <summary className="flex min-h-11 list-none items-center gap-2 rounded-xl px-3 text-sm font-bold text-teal-800 transition hover:bg-teal-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 [&::-webkit-details-marker]:hidden">
              Sign in
              <ChevronDownIcon
                aria-hidden="true"
                className="size-4 transition-transform group-open:rotate-180"
              />
            </summary>
            <nav
              aria-label="Sign-in options"
              className="absolute right-0 top-[calc(100%+0.5rem)] w-60 overflow-hidden rounded-2xl border border-slate-200 bg-white p-2 shadow-xl shadow-slate-950/10"
            >
              <Link
                className="block rounded-xl px-4 py-3 text-sm font-semibold text-slate-800 transition hover:bg-teal-50 hover:text-teal-800 focus-visible:outline-2 focus-visible:outline-teal-700"
                href="/citizen/login"
              >
                Citizen sign in
              </Link>
              <Link
                className="block rounded-xl px-4 py-3 text-sm font-semibold text-slate-800 transition hover:bg-teal-50 hover:text-teal-800 focus-visible:outline-2 focus-visible:outline-teal-700"
                href="/professional/login"
              >
                Professional sign in
              </Link>
            </nav>
          </details>

          <nav
            aria-label="Mobile primary navigation"
            className="order-3 flex w-full items-center justify-center gap-6 border-t border-slate-100 pt-3 md:hidden"
          >
            <a className={navigationLinkClass} href="#how-it-works">
              How it works
            </a>
            <Link className={navigationLinkClass} href="/professional/register">
              For professionals
            </Link>
          </nav>
        </div>
      </header>

      <main id="main-content">
        <section className="bg-[#fbfefd]">
          <div className="grid w-full xl:min-h-[clamp(32rem,64vh,40.625rem)] xl:grid-cols-[48.5%_51.5%]">
            <div className="flex items-center px-5 py-16 sm:px-8 lg:px-16 xl:pl-[clamp(5rem,7.75vw,7rem)] xl:pr-10">
              <div className="max-w-[640px]">
                <p className="text-xs font-extrabold uppercase tracking-[0.28em] text-teal-700 sm:text-sm">
                  Connected care, made clear
                </p>
                <h1
                  aria-label="Care that follows your story."
                  className="mt-8 font-display text-[2.75rem] font-extrabold leading-[0.99] tracking-[-0.055em] text-slate-950 sm:text-6xl xl:text-[4.5rem]"
                >
                  Care that follows
                  <br />
                  your story.
                </h1>
                <p className="mt-9 max-w-[535px] text-lg leading-8 text-indigo-900/75 sm:text-xl sm:leading-9">
                  HealthLink brings verified providers, appointments, and health records together—so every next step feels simpler.
                </p>

                <div className="mt-9 flex flex-col gap-4 sm:flex-row">
                  <Link
                    className="inline-flex min-h-14 items-center justify-center rounded-xl bg-teal-700 px-7 text-base font-bold text-white shadow-lg shadow-teal-900/15 transition hover:-translate-y-0.5 hover:bg-teal-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 sm:min-w-[278px]"
                    href="/citizen/register"
                  >
                    Create citizen account
                  </Link>
                  <Link
                    className="inline-flex min-h-14 items-center justify-center rounded-xl border border-teal-700 bg-white px-7 text-base font-bold text-indigo-950 transition hover:-translate-y-0.5 hover:bg-teal-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 sm:min-w-[278px]"
                    href="/citizen/login?returnTo=%2Fcitizen%2Fdoctors%2Fsearch"
                  >
                    Find a verified doctor
                  </Link>
                </div>
              </div>
            </div>

            <div className="relative min-h-[500px] overflow-hidden bg-[#e8fbfa] sm:min-h-[580px] xl:min-h-0">
              <Image
                alt="A Bangladeshi doctor representing connected care"
                className="object-cover object-right"
                fill
                priority
                sizes="(min-width: 1280px) 50vw, 100vw"
                src="/images/healthlink-doctor-hero.png"
                unoptimized
              />
            </div>
          </div>
        </section>

        <section className="bg-teal-800 px-5 py-9 text-white sm:px-8 sm:py-10" id="how-it-works">
          <div className="mx-auto w-full max-w-[1180px]">
            <h2 className="text-center font-display text-2xl font-bold tracking-[-0.035em] sm:text-3xl">
              How HealthLink works
            </h2>

            <ol className="mt-8 grid gap-0 md:grid-cols-3">
              {careSteps.map((step, index) => {
                const Icon = step.icon;

                return (
                  <li
                    className={`flex items-start gap-5 py-6 md:px-8 md:py-2 ${
                      index > 0 ? "border-t border-teal-200/35 md:border-l md:border-t-0" : ""
                    }`}
                    key={step.title}
                  >
                    <span className="flex size-16 shrink-0 items-center justify-center rounded-full bg-teal-50 text-teal-800">
                      <Icon aria-hidden="true" className="size-8" />
                    </span>
                    <div className="pt-1">
                      <div className="flex items-baseline gap-3">
                        <span className="text-3xl font-bold text-teal-200">{step.number}</span>
                        <h3 className="text-lg font-bold tracking-tight">{step.title}</h3>
                      </div>
                      <p className="mt-2 max-w-[15rem] text-sm leading-6 text-teal-50/85">{step.description}</p>
                    </div>
                  </li>
                );
              })}
            </ol>
          </div>
        </section>

        <section
          className="bg-white px-5 py-20 sm:px-8 sm:py-24 lg:px-[clamp(3rem,7.75vw,7rem)] lg:py-28"
          id="our-purpose"
        >
          <div className="mx-auto grid w-full max-w-[1280px] gap-14 lg:grid-cols-[0.9fr_1.1fr] lg:gap-24">
            <div className="max-w-xl">
              <p className="text-xs font-extrabold uppercase tracking-[0.28em] text-teal-700 sm:text-sm">
                Our purpose
              </p>
              <h2 className="mt-6 font-display text-4xl font-extrabold leading-[1.06] tracking-[-0.045em] text-slate-950 sm:text-5xl">
                Healthcare should feel connected, not complicated.
              </h2>
              <p className="mt-7 max-w-lg text-lg leading-8 text-indigo-900/70">
                HealthLink is shaped around clarity, continuity, and trust—so the experience of navigating care feels as thoughtful as the care itself.
              </p>
            </div>

            <ol className="border-t border-slate-200">
              {carePrinciples.map((principle) => (
                <li
                  className="grid gap-4 border-b border-slate-200 py-7 sm:grid-cols-[3.5rem_1fr] sm:gap-6 sm:py-8"
                  key={principle.number}
                >
                  <span className="font-display text-sm font-bold text-teal-700">
                    {principle.number}
                  </span>
                  <div>
                    <h3 className="font-display text-xl font-bold tracking-[-0.025em] text-slate-950 sm:text-2xl">
                      {principle.title}
                    </h3>
                    <p className="mt-2 max-w-xl leading-7 text-slate-600">
                      {principle.description}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section
          className="bg-[#e8f9f7] px-5 py-20 text-center sm:px-8 sm:py-24"
          id="shared-foundation"
        >
          <div className="mx-auto max-w-4xl">
            <p className="text-xs font-extrabold uppercase tracking-[0.28em] text-teal-700 sm:text-sm">
              A shared foundation
            </p>
            <h2 className="mt-6 font-display text-4xl font-extrabold leading-[1.08] tracking-[-0.045em] text-slate-950 sm:text-5xl">
              Better context supports better conversations.
            </h2>
            <p className="mx-auto mt-7 max-w-2xl text-lg leading-8 text-indigo-900/70">
              HealthLink is designed to keep people, professionals, and care information aligned around the same clear story.
            </p>
          </div>
        </section>
      </main>

      <footer className="border-t border-teal-900/10 bg-white px-5 py-8 sm:px-8 lg:px-[clamp(3rem,7.75vw,7rem)]">
        <div className="mx-auto flex w-full max-w-[1280px] flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <HealthLinkMark className="size-9 text-teal-700" />
            <div>
              <p className="font-display font-extrabold tracking-[-0.025em] text-slate-950">
                Health<span className="text-teal-700">Link</span>
              </p>
              <p className="mt-0.5 text-sm text-slate-500">
                Connected care, centered on people.
              </p>
            </div>
          </div>
          <p className="text-sm text-slate-500">© 2026 HealthLink.</p>
        </div>
      </footer>
    </div>
  );
}
