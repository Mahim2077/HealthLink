"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { AppointmentBookForm } from "@/components/citizen/appointment-book-form";
import { usePortalAuth } from "@/components/auth/auth-provider";
import {
  EmptyState,
  LoadingState,
} from "@/components/ui/async-state";
import type { AppointmentBookingResponse } from "@/lib/appointments/types";
import { loadDoctorProfile } from "@/lib/doctors/api";
import type { DoctorProfile } from "@/lib/doctors/types";
import { citizenErrorMessage } from "@/lib/citizen/presentation";

function BookContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialDoctorUserId = searchParams.get("doctor_user_id") ?? "";
  const [doctor, setDoctor] = useState<DoctorProfile | null>(null);
  const [doctorError, setDoctorError] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    if (!initialDoctorUserId) return;
    void loadDoctorProfile(initialDoctorUserId).then(profile => {
      if (active) setDoctor(profile);
    }).catch(error => {
      if (active) setDoctorError(citizenErrorMessage(error, "We could not load this doctor. Please choose a doctor again."));
    });
    return () => { active = false; };
  }, [initialDoctorUserId]);
  const [confirmation, setConfirmation] =
    useState<AppointmentBookingResponse | null>(null);

  const handleBooked = useCallback(
    (response: AppointmentBookingResponse) => {
      setConfirmation(response);
      const params = new URLSearchParams({
        booked: "1",
        serial: String(response.serial_number),
      });
      router.replace(`/citizen/appointments?${params.toString()}`);
    },
    [router],
  );

  if (confirmation) {
    return (
      <main className="mx-auto w-full max-w-3xl flex-1 px-5 py-12 sm:px-8" id="main-content">
        <div className="rounded-[1.5rem] border border-emerald-200 bg-emerald-50 p-6">
          <p className="text-xs font-bold uppercase tracking-[0.15em] text-emerald-700">
            Appointment booked
          </p>
          <h1 className="mt-3 font-display text-2xl font-bold tracking-[-0.04em] text-slate-950 sm:text-3xl">
            Serial number #{confirmation.serial_number}
          </h1>
          <p className="mt-2 text-sm text-slate-700">
            at <span className="font-semibold">{confirmation.facility_name}</span> on{" "}
            {confirmation.appointment_date}
          </p>
          <Link
            className="mt-5 inline-flex min-h-11 items-center justify-center rounded-xl bg-teal-700 px-5 text-sm font-bold text-white"
            href="/citizen/appointments"
          >
            View my appointments
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main
      className="mx-auto w-full max-w-3xl flex-1 px-5 py-10 sm:px-8 lg:px-10"
      id="main-content"
    >
      <div className="border-b border-slate-200 pb-7">
        <Link
          className="text-sm font-bold text-teal-700 hover:text-teal-900"
          href="/citizen/appointments"
        >
          ← My appointments
        </Link>
        <p className="mt-6 text-xs font-bold uppercase tracking-[0.15em] text-teal-700">
          New appointment
        </p>
        <h1 className="mt-3 font-display text-3xl font-bold tracking-[-0.04em] text-slate-950 sm:text-4xl">
          Book an appointment
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
          Choose a date from your doctor&apos;s weekly practice days. You will receive a serial number for the queue.
        </p>
      </div>

      <section className="mt-8 rounded-[1.5rem] border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-base font-bold uppercase tracking-[0.15em] text-teal-700">
          Appointment details
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          Fields marked optional can be left blank. The reason helps the doctor
          prepare for your visit.
        </p>
        <div className="mt-5">
          {doctorError ? <p role="alert" className="mb-4 text-sm text-rose-700">{doctorError}</p> : null}
          {!initialDoctorUserId || doctorError || (doctor && !doctor.practice_days.some(day => day.status === "ACTIVE" && day.facility_id === doctor.facility_id)) ? (
            <EmptyState title="Choose an available doctor" message="Find a verified doctor with published practice days before booking." action={<Link className="font-bold text-teal-700" href="/citizen/doctors/search">Find a doctor</Link>} />
          ) : doctor?.id === initialDoctorUserId ? (
            <AppointmentBookForm key={doctor.id} doctor={doctor} onBooked={handleBooked} />
          ) : <LoadingState label="Loading doctor" description="Checking the current practice schedule." />}
        </div>
      </section>
    </main>
  );
}

function CitizenGuard({ children }: { children: React.ReactNode }) {
  const params = useSearchParams();
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
              href={`/citizen/login?returnTo=${encodeURIComponent(`/citizen/appointments/book?${params.toString()}`)}`}
            >
              Sign in to Citizen Portal
            </Link>
          }
          message="Sign in to book a verified doctor appointment."
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

export default function CitizenBookAppointmentPage() {
  return (
    <>
      <CitizenGuard>
        <BookContent />
      </CitizenGuard>
    </>
  );
}
