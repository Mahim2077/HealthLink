"use client";

import Link from "next/link";
import { useEffect, useId, useState, type ReactNode } from "react";
import { loadAdminOverview, loadCitizenOverview, loadProfessionalOverview, type AdminOverview, type CitizenOverview, type ProfessionalOverview } from "@/lib/overview";
import { ErrorState, LoadingState } from "@/components/ui/async-state";

type Card = { title: string; value: string; detail: string; href: string };

function OverviewCards({ cards }: { cards: Card[] }) {
  return <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{cards.map(card => (
    <Link key={card.title} href={card.href} className="hl-card min-w-0 break-words p-5 transition hover:border-teal-400 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-teal-700">
      <h3 className="text-sm font-semibold text-slate-600">{card.title}</h3>
      <p className="mt-2 text-lg font-bold text-slate-950">{card.value}</p>
      <p className="mt-2 text-sm leading-6 text-slate-600">{card.detail}</p>
    </Link>
  ))}</div>;
}

function OverviewLoader<T>({ title, load, children }: { title: string; load: () => Promise<T>; children: (data: T) => ReactNode }) {
  const id = useId();
  const [state, setState] = useState<{ data: T } | { error: string } | null>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    void load().then(data => { if (active) setState({ data }); }, () => {
      if (active) setState({ error: "The care overview could not be loaded. Your existing tools are still available below." });
    });
    return () => { active = false; };
  }, [load, attempt]);
  return <section className="mt-8" aria-labelledby={id}>
    <h2 id={id} className="text-2xl font-bold tracking-tight text-slate-950">{title}</h2>
    {state === null ? <LoadingState label="Loading care overview" /> : "error" in state ?
      <ErrorState title="Overview unavailable" message={state.error} onAction={() => { setState(null); setAttempt(value => value + 1); }} /> : children(state.data)}
  </section>;
}

export function CitizenCareOverview({ load = loadCitizenOverview }: { load?: () => Promise<CitizenOverview> }) {
  return <OverviewLoader title="Your care at a glance" load={load}>{data => {
    const appointment = data.upcoming_appointment;
    const prescription = data.recent_prescription;
    const report = data.latest_report;
    return <>
      <OverviewCards cards={[
        { title: "Upcoming appointment", value: appointment ? appointment.appointment_date : "Nothing booked", detail: appointment ? `${appointment.facility_name} · Serial ${appointment.serial_number}` : "Find a doctor when you need care.", href: "/citizen/appointments" },
        { title: "Recent prescription", value: prescription ? "Your latest finalized visit" : "No finalized prescription", detail: "Review the original doctor's instructions; PDFs are regenerated when requested.", href: prescription ? `/citizen/prescriptions/${prescription.id}` : "/citizen/medical-history" },
        { title: "Latest diagnostic result", value: report?.test_name ?? "No finalized report", detail: report ? `Reported ${report.report_date}` : "Tests, reports and trends stay together.", href: report ? `/citizen/diagnostic-tests/${report.diagnostic_test_id}` : "/citizen/diagnostic-tests" },
        { title: "Emergency profile", value: data.emergency_profile_updated_at ? "Profile saved" : "Not set up yet", detail: "Keep your emergency information current.", href: "/citizen/emergency-profile" },
        { title: "Medical history", value: "Your clinical timeline", detail: "Review finalized visits and prescriptions.", href: "/citizen/medical-history" },
        { title: "Privacy & access", value: "You control sharing", detail: "Review record access and manage scoped grants.", href: "/citizen/privacy" },
        { title: "AI assistant", value: "Understand your records", detail: "Educational explanations only—not diagnosis or prescriptions.", href: "/citizen/ai-assistant" },
        { title: "Saved reminders", value: `${data.active_reminders} active today`, detail: `${data.unread_notifications} unread notifications. Automatic reminder delivery is not enabled.`, href: "/citizen/reminders" },
      ]} />
    </>;
  }}</OverviewLoader>;
}

export function ProfessionalCareOverview({ role, load = loadProfessionalOverview }: { role: "DOCTOR" | "LAB_TECHNICIAN"; load?: () => Promise<ProfessionalOverview> }) {
  return <OverviewLoader key={role} title={role === "DOCTOR" ? "Today's care overview" : "Your diagnostic workload"} load={load}>{data => {
    if (data.role_code !== role) return <p role="alert" className="mt-4 text-rose-700">The active role changed. Reload your workspace.</p>;
    const doctor = role === "DOCTOR";
    const cards: Card[] = [
      { title: doctor ? "Requested diagnostics" : "Assigned requests", value: String(data.requested_tests), detail: doctor ? "Tests requested by your selected doctor role." : "Assigned to this lab role at your active facility.", href: "/professional/diagnostics" },
      { title: "Tests in progress", value: String(data.in_progress_tests), detail: "Continue work in the diagnostic queue.", href: "/professional/diagnostics" },
    ];
    if (!doctor) cards.push(
      { title: "Draft reports", value: String(data.draft_reports), detail: "Your reports awaiting completion and finalization.", href: "/professional/diagnostics" },
      { title: "Finalized reports", value: String(data.finalized_reports), detail: "Your finalized assigned reports are immutable.", href: "/professional/diagnostics" },
    );
    if (doctor && data.recent_prescription) cards.push({ title: "Recent authored prescription", value: "Review your latest record", detail: "Existing author-only editing rules still apply.", href: `/professional/prescriptions/${data.recent_prescription.id}` });
    return <>
      {doctor ? <div className="mt-4 space-y-3">{data.chambers.length ? data.chambers.map((chamber, index) => (
        <article key={`${chamber.facility_name}-${index}`} className="hl-card min-w-0 break-words p-5">
          <h3 className="font-bold">{chamber.facility_name}</h3>
          <p className="mt-2 text-sm text-slate-600">{chamber.status === "ACTIVE" ? "In progress" : chamber.status === "COMPLETED" ? "Closed for today" : "Not started"} · {chamber.waiting_count} waiting · {chamber.current_serial === null ? "No current patient" : `Current serial ${chamber.current_serial}`}</p>
          <Link className="mt-2 inline-flex min-h-11 items-center font-bold text-sky-700" href="/professional/chamber">Open chamber queue</Link>
        </article>
      )) : <p className="text-sm text-slate-600">No chamber session for {data.today}. Review practice hours in <Link className="font-semibold text-sky-800 underline underline-offset-2" href="/professional/settings/practice">Settings</Link> or open the chamber to start eligible practice.</p>}
      {data.chambers_has_more ? <p className="text-sm text-slate-600">Showing the first 10 chambers. Open the chamber workspace for other sessions.</p> : null}</div> : null}
      <OverviewCards cards={cards} />
    </>;
  }}</OverviewLoader>;
}

export function AdminCareOverview({ load = loadAdminOverview }: { load?: () => Promise<AdminOverview> }) {
  return <OverviewLoader title="Operational overview" load={load}>{data => <OverviewCards cards={[
    { title: "Pending role applications", value: String(data.pending_professional_registrations), detail: "Applications awaiting an administrator's review.", href: "/admin/professional-registrations" },
    { title: "Active facility registry", value: String(data.active_facilities), detail: "Active facilities in HealthLink, not simulated analytics.", href: "/admin/facilities" },
    { title: "Location confirmation needed", value: String(data.facilities_needing_location), detail: "Confirm facility addresses before nearby search can include them.", href: "/admin/facilities" },
  ]} />}</OverviewLoader>;
}
