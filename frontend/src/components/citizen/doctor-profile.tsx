"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { CitizenShell } from "@/components/citizen/citizen-shell";
import { usePortalAuth } from "@/components/auth/auth-provider";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/ui/async-state";
import { loadDoctorProfile } from "@/lib/doctors/api";
import type {
  DoctorProfile,
  PracticeDay,
  PracticeWeekday,
} from "@/lib/doctors/types";
import { citizenErrorMessage } from "@/lib/citizen/presentation";

const WEEKDAY_ORDER: PracticeWeekday[] = [
  "SUNDAY",
  "MONDAY",
  "TUESDAY",
  "WEDNESDAY",
  "THURSDAY",
  "FRIDAY",
  "SATURDAY",
];

const WEEKDAY_LABEL: Record<PracticeWeekday, string> = {
  FRIDAY: "Friday",
  MONDAY: "Monday",
  SATURDAY: "Saturday",
  SUNDAY: "Sunday",
  THURSDAY: "Thursday",
  TUESDAY: "Tuesday",
  WEDNESDAY: "Wednesday",
};

function formatTime(value: string): string {
  if (value.length >= 5) {
    return value.slice(0, 5);
  }
  return value;
}

function asDateTime(value: string | null): string {
  if (!value) {
    return "Not recorded";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function sortPracticeDays(days: PracticeDay[]): PracticeDay[] {
  return [...days].sort((left, right) => {
    const leftIndex = WEEKDAY_ORDER.indexOf(left.weekday);
    const rightIndex = WEEKDAY_ORDER.indexOf(right.weekday);
    if (leftIndex !== rightIndex) {
      return leftIndex - rightIndex;
    }
    return left.start_time.localeCompare(right.start_time);
  });
}

function PracticeDayRow({ day }: { day: PracticeDay }) {
  return (
    <li
      className="flex flex-col gap-2 rounded-xl border border-slate-200 bg-slate-50/70 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
      data-testid="practice-day-row"
    >
      <div>
        <p className="text-sm font-bold text-slate-950">
          {WEEKDAY_LABEL[day.weekday]}
        </p>
        <p className="mt-1 text-sm text-slate-700">
          {formatTime(day.start_time)} – {formatTime(day.end_time)}
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="rounded-full bg-sky-50 px-2.5 py-1 font-bold text-sky-800">
          {day.facility_name}
        </span>
        <span className="rounded-full bg-slate-200 px-2.5 py-1 font-bold text-slate-700">
          Up to {day.max_patients} patients
        </span>
        <span
          className={`rounded-full px-2.5 py-1 font-bold ${
            day.status === "ACTIVE"
              ? "bg-emerald-50 text-emerald-700"
              : "bg-slate-200 text-slate-700"
          }`}
        >
          {day.status}
        </span>
      </div>
    </li>
  );
}

function ProfileContent({
  doctorUserId,
  loadAction,
}: {
  doctorUserId: string;
  loadAction: (id: string) => Promise<DoctorProfile>;
}) {
  const [profile, setProfile] = useState<DoctorProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  const reload = useCallback(() => {
    setProfile(null);
    setError(null);
    setVersion((value) => value + 1);
  }, []);

  useEffect(() => {
    let active = true;
    void loadAction(doctorUserId).then(
      (value) => {
        if (active) setProfile(value);
      },
      (reason: unknown) => {
        if (active) {
          setError(
            citizenErrorMessage(
              reason,
              "We could not load this doctor right now.",
            ),
          );
        }
      },
    );
    return () => {
      active = false;
    };
  }, [doctorUserId, loadAction, version]);

  if (!profile && !error) {
    return (
      <main className="flex flex-1 items-center px-5 py-12" id="main-content">
        <LoadingState
          description="Loading the verified doctor's profile and practice schedule."
          label="Loading doctor"
        />
      </main>
    );
  }

  if (error) {
    return (
      <main className="flex flex-1 items-center px-5 py-12" id="main-content">
        <ErrorState
          message={error}
          onAction={reload}
          title="Doctor profile unavailable"
        />
      </main>
    );
  }

  if (!profile) {
    return null;
  }

  const activeDays = profile.practice_days.filter(
    (day) => day.status === "ACTIVE",
  );
  const sortedDays = sortPracticeDays(activeDays);

  return (
    <main
      className="mx-auto w-full max-w-5xl flex-1 px-5 py-10 sm:px-8 lg:px-10"
      id="main-content"
    >
      <div className="border-b border-slate-200 pb-7">
        <Link
          className="text-sm font-bold text-teal-700 hover:text-teal-900"
          href="/citizen/doctors/search"
        >
          ← Doctor search
        </Link>
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <p className="text-xs font-bold uppercase tracking-[0.15em] text-teal-700">
            Verified doctor
          </p>
          <span
            className={`rounded-full px-3 py-1 text-xs font-bold ${
              profile.verified
                ? "bg-emerald-50 text-emerald-700"
                : "bg-slate-100 text-slate-600"
            }`}
          >
            {profile.verified ? "VERIFIED" : "UNVERIFIED"}
          </span>
        </div>
        <h1 className="mt-3 font-display text-3xl font-bold tracking-[-0.04em] text-slate-950 sm:text-4xl">
          {profile.name}
        </h1>
        <p className="mt-2 text-sm text-slate-600">{profile.designation}</p>
        <p className="mt-1 text-sm text-slate-700">
          <span className="font-semibold">{profile.facility_name}</span>
          <span className="ml-2 text-xs uppercase tracking-wide text-slate-500">
            {profile.facility_type}
          </span>
        </p>
        {profile.specialization ? (
          <p className="mt-2 text-sm text-slate-600">
            Specialization: {profile.specialization}
          </p>
        ) : null}
        <div className="mt-5 flex flex-wrap gap-3">
          <Link
            className="inline-flex min-h-11 items-center justify-center rounded-xl bg-teal-700 px-5 text-sm font-bold text-white transition hover:bg-teal-800"
            data-testid="book-appointment-cta"
            href={`/citizen/appointments/book?doctor_user_id=${encodeURIComponent(
              profile.id,
            )}&facility_id=${encodeURIComponent(profile.facility_id)}`}
          >
            Book appointment
          </Link>
        </div>
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-[0.85fr_1.15fr]">
        <section className="rounded-[1.5rem] border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-base font-bold uppercase tracking-[0.15em] text-teal-700">
            Contact
          </h2>
          <p className="mt-2 break-words text-sm text-slate-700">
            {profile.email}
          </p>
          <h2 className="mt-6 text-base font-bold uppercase tracking-[0.15em] text-teal-700">
            Verification
          </h2>
          <p className="mt-2 text-sm text-slate-700">
            Submitted: {asDateTime(profile.submitted_at)}
          </p>
          <p className="mt-1 text-sm text-slate-700">
            Verified at: {asDateTime(profile.verified_at)}
          </p>
        </section>

        <section className="rounded-[1.5rem] border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-base font-bold uppercase tracking-[0.15em] text-teal-700">
            Weekly practice windows
          </h2>
          {sortedDays.length === 0 ? (
            <p className="mt-3 text-sm text-slate-600">
              This doctor has not published any active weekly practice windows
              yet.
            </p>
          ) : (
            <ul className="mt-4 grid gap-3" data-testid="practice-day-list">
              {sortedDays.map((day) => (
                <PracticeDayRow day={day} key={day.id} />
              ))}
            </ul>
          )}
        </section>
      </div>
    </main>
  );
}

function CitizenGuard({ children }: { children: React.ReactNode }) {
  const auth = usePortalAuth("CITIZEN");
  const [hydrationFailed, setHydrationFailed] = useState(false);
  const status = auth.status;
  const refresh = auth.refreshSession;

  useEffect(() => {
    if (status === "authenticated") {
      return;
    }
    let active = true;
    void refresh().catch(() => {
      if (active) setHydrationFailed(true);
    });
    return () => {
      active = false;
    };
  }, [refresh, status]);

  if (status === "unauthenticated" && !hydrationFailed) {
    return (
      <main className="flex flex-1 items-center px-5 py-12" id="main-content">
        <LoadingState
          description="Checking for an active Citizen Portal session."
          label="Checking Citizen session"
        />
      </main>
    );
  }

  if (status === "unauthenticated") {
    return (
      <main className="flex flex-1 items-center px-5 py-12" id="main-content">
        <EmptyState
          action={
            <Link
              className="inline-flex min-h-11 items-center justify-center rounded-xl bg-teal-700 px-5 text-sm font-bold text-white"
              href="/citizen/login"
            >
              Sign in to Citizen Portal
            </Link>
          }
          message="Sign in to view verified doctors."
          title="Citizen sign in required"
        />
      </main>
    );
  }

  if (!auth.isRequiredPortal) {
    return (
      <main className="flex flex-1 items-center px-5 py-12" id="main-content">
        <EmptyState
          message="This session belongs to another HealthLink portal."
          title="Citizen Portal access required"
        />
      </main>
    );
  }

  return <>{children}</>;
}

export function DoctorProfileView({
  doctorUserId,
  loadAction = loadDoctorProfile,
}: {
  doctorUserId: string;
  loadAction?: (id: string) => Promise<DoctorProfile>;
}) {
  return (
    <CitizenShell>
      <CitizenGuard>
        <ProfileContent doctorUserId={doctorUserId} loadAction={loadAction} />
      </CitizenGuard>
    </CitizenShell>
  );
}