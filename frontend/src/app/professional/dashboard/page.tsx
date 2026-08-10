import Link from "next/link";

import { PracticeScheduleEditor } from "@/components/professional/practice-schedule-editor";
import { ProfessionalPortal } from "@/components/professional/professional-portal";

export default function ProfessionalDashboardPage() {
  return (
    <ProfessionalPortal
      mode="dashboard"
      verifiedDoctorSlot={
        <div className="space-y-6">
          <PracticeScheduleEditor />
          <ChamberDashboardCard />
          <ConsultationsDashboardCard />
        </div>
      }
    />
  );
}

function ChamberDashboardCard() {
  // The dashboard surfaces a Chamber shortcut; the dedicated
  // /professional/chamber page owns the live queue + actions.
  return (
    <section className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
      <header className="flex flex-col gap-3 border-b border-slate-200 pb-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.15em] text-sky-700">
            Chamber
          </p>
          <h2 className="mt-2 text-2xl font-bold text-slate-950">
            Today&rsquo;s chamber queue
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            Open today&rsquo;s chamber, call the next serial, and complete or
            skip patients.
          </p>
        </div>
        <Link
          className="inline-flex min-h-11 items-center rounded-xl bg-sky-700 px-5 text-sm font-bold text-white"
          href="/professional/chamber"
        >
          Open chamber
        </Link>
      </header>
      <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-5 text-sm text-slate-600">
        <p>
          The chamber page calls today&rsquo;s session, lists waiting serials,
          and exposes the seven chamber actions.
        </p>
      </div>
    </section>
  );
}

function ConsultationsDashboardCard() {
  // The dashboard surfaces a Consultations shortcut; the dedicated
  // /professional/visits page owns the live consultation workspace for
  // the doctor with the current serial.
  return (
    <section className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
      <header className="flex flex-col gap-3 border-b border-slate-200 pb-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.15em] text-sky-700">
            Visits
          </p>
          <h2 className="mt-2 text-2xl font-bold text-slate-950">
            Today&rsquo;s consultations
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            Open the chart for the current serial, draft notes, and finalize
            the visit.
          </p>
        </div>
        <Link
          className="inline-flex min-h-11 items-center rounded-xl bg-sky-700 px-5 text-sm font-bold text-white"
          href="/professional/visits"
        >
          Open consultations
        </Link>
      </header>
      <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-5 text-sm text-slate-600">
        <p>
          The visits page loads the current patient, lets you open the visit
          draft, edit clinical fields, and save progress.
        </p>
      </div>
    </section>
  );
}
