"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { CitizenShell } from "@/components/citizen/citizen-shell";
import { usePortalAuth } from "@/components/auth/auth-provider";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/ui/async-state";
import { listMyAppointments } from "@/lib/appointments/api";
import type {
  AppointmentListEntry,
  AppointmentListResponse,
  AppointmentStatus,
} from "@/lib/appointments/types";
import { citizenErrorMessage } from "@/lib/citizen/presentation";

const STATUS_ORDER: AppointmentStatus[] = ["BOOKED", "COMPLETED", "CANCELLED"];

const STATUS_LABEL: Record<AppointmentStatus, string> = {
  BOOKED: "Booked",
  CANCELLED: "Cancelled",
  COMPLETED: "Completed",
};

const STATUS_STYLE: Record<AppointmentStatus, string> = {
  BOOKED: "bg-sky-50 text-sky-800",
  CANCELLED: "bg-slate-200 text-slate-700",
  COMPLETED: "bg-emerald-50 text-emerald-700",
};

function formatDate(value: string): string {
  const parsed = new Date(value + "T00:00:00");
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("en-BD", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(parsed);
}

function formatTimestamp(value: string | null): string {
  if (!value) {
    return "Not recorded";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}

function groupByStatus(
  appointments: AppointmentListEntry[],
): Record<AppointmentStatus, AppointmentListEntry[]> {
  const grouped: Record<AppointmentStatus, AppointmentListEntry[]> = {
    BOOKED: [],
    CANCELLED: [],
    COMPLETED: [],
  };
  for (const appointment of appointments) {
    grouped[appointment.status].push(appointment);
  }
  for (const status of STATUS_ORDER) {
    grouped[status].sort((left, right) =>
      left.appointment_date.localeCompare(right.appointment_date),
    );
  }
  return grouped;
}

function AppointmentRow({ appointment }: { appointment: AppointmentListEntry }) {
  return (
    <article
      className="rounded-[1.4rem] border border-slate-200 bg-white p-5 shadow-sm"
      data-testid="appointment-row"
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-bold text-slate-950">
              {appointment.doctor_name}
            </h2>
            <span
              className={`rounded-full px-2.5 py-1 text-xs font-bold ${
                STATUS_STYLE[appointment.status]
              }`}
              data-testid="appointment-status"
            >
              {STATUS_LABEL[appointment.status]}
            </span>
          </div>
          <p className="mt-2 text-sm text-slate-700">
            <span className="font-semibold">{appointment.facility_name}</span>
          </p>
          <p className="mt-1 text-sm text-slate-600">
            Date: {formatDate(appointment.appointment_date)}
          </p>
          <p className="mt-1 text-sm text-slate-600">
            Serial #{appointment.serial_number}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Booked at: {formatTimestamp(appointment.booked_at)}
          </p>
          {appointment.cancelled_at ? (
            <p className="mt-1 text-xs text-slate-500">
              Cancelled at: {formatTimestamp(appointment.cancelled_at)}
            </p>
          ) : null}
          {appointment.completed_at ? (
            <p className="mt-1 text-xs text-slate-500">
              Completed at: {formatTimestamp(appointment.completed_at)}
            </p>
          ) : null}
        </div>
      </div>
    </article>
  );
}

function AppointmentsContent({
  loadAction,
}: {
  loadAction: () => Promise<AppointmentListResponse>;
}) {
  const searchParams = useSearchParams();
  const justBookedSerial = searchParams.get("serial");
  const [appointments, setAppointments] = useState<AppointmentListEntry[] | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  const reload = useCallback(() => {
    setAppointments(null);
    setError(null);
    setVersion((value) => value + 1);
  }, []);

  useEffect(() => {
    let active = true;
    void loadAction().then(
      (response) => {
        if (active) {
          setAppointments(response.appointments);
        }
      },
      (reason: unknown) => {
        if (active) {
          setError(
            citizenErrorMessage(
              reason,
              "We could not load your appointments right now.",
            ),
          );
        }
      },
    );
    return () => {
      active = false;
    };
  }, [loadAction, version]);

  if (error) {
    return (
      <main className="mx-auto w-full max-w-5xl flex-1 px-5 py-12 sm:px-8" id="main-content">
        <ErrorState
          message={error}
          onAction={reload}
          title="Appointments unavailable"
        />
      </main>
    );
  }

  if (!appointments) {
    return (
      <main className="flex flex-1 items-center px-5 py-12" id="main-content">
        <LoadingState
          description="Loading your booked, completed, and cancelled appointments."
          label="Loading appointments"
        />
      </main>
    );
  }

  const grouped = groupByStatus(appointments);

  return (
    <main
      className="mx-auto w-full max-w-5xl flex-1 px-5 py-10 sm:px-8 lg:px-10"
      id="main-content"
    >
      <div className="border-b border-slate-200 pb-7">
        <Link
          className="text-sm font-bold text-teal-700 hover:text-teal-900"
          href="/citizen/dashboard"
        >
          ← Citizen Dashboard
        </Link>
        <p className="mt-6 text-xs font-bold uppercase tracking-[0.15em] text-teal-700">
          Appointments
        </p>
        <h1 className="mt-3 font-display text-3xl font-bold tracking-[-0.04em] text-slate-950 sm:text-4xl">
          My appointments
        </h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">
          Track every appointment you have booked with verified HealthLink
          doctors. Serial numbers are assigned at booking and stay with you for
          the lifetime of the appointment.
        </p>
        {justBookedSerial ? (
          <p
            className="mt-5 inline-block rounded-full bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700"
            data-testid="just-booked-banner"
          >
            Booking confirmed — serial #{justBookedSerial}
          </p>
        ) : null}
      </div>

      <div className="mt-7 flex flex-wrap items-center gap-3">
        <Link
          className="inline-flex min-h-11 items-center justify-center rounded-xl bg-teal-700 px-5 text-sm font-bold text-white transition hover:bg-teal-800"
          data-testid="book-appointment-cta"
          href="/citizen/appointments/book"
        >
          Book new appointment
        </Link>
        <Link
          className="inline-flex min-h-11 items-center justify-center rounded-xl border border-slate-300 px-5 text-sm font-bold text-slate-700 transition hover:border-slate-400"
          href="/citizen/doctors/search"
        >
          Find a doctor
        </Link>
      </div>

      {appointments.length === 0 ? (
        <div className="mt-8">
          <EmptyState
            action={
              <Link
                className="inline-flex min-h-11 items-center justify-center rounded-xl bg-teal-700 px-5 text-sm font-bold text-white"
                href="/citizen/doctors/search"
              >
                Find a doctor
              </Link>
            }
            message="You have not booked any appointments yet."
            title="No appointments"
          />
        </div>
      ) : (
        <div className="mt-8 space-y-8" data-testid="appointment-groups">
          {STATUS_ORDER.map((status) => {
            const rows = grouped[status];
            if (rows.length === 0) {
              return null;
            }
            return (
              <section key={status} aria-labelledby={`status-${status}`}>
                <h2
                  className="text-base font-bold uppercase tracking-[0.15em] text-slate-700"
                  id={`status-${status}`}
                >
                  {STATUS_LABEL[status]} ({rows.length})
                </h2>
                <div className="mt-4 grid gap-4">
                  {rows.map((appointment) => (
                    <AppointmentRow
                      appointment={appointment}
                      key={appointment.id}
                    />
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </main>
  );
}

function CitizenGuard({ children }: { children: React.ReactNode }) {
  const auth = usePortalAuth("CITIZEN");
  const status = auth.status;
  const refresh = auth.refreshSession;
  const [hydrationFailed, setHydrationFailed] = useState(false);

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
          message="Sign in to view your appointments."
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

export function AppointmentsView({
  loadAction = listMyAppointments,
}: {
  loadAction?: () => Promise<AppointmentListResponse>;
} = {}) {
  return (
    <CitizenShell>
      <CitizenGuard>
        <AppointmentsContent loadAction={loadAction} />
      </CitizenGuard>
    </CitizenShell>
  );
}

export default function CitizenAppointmentsPage() {
  return <AppointmentsView />;
}