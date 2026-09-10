import {
  ArrowRightIcon,
  ChatBubbleBottomCenterTextIcon,
  QueueListIcon,
} from "@heroicons/react/24/outline";
import Link from "next/link";

import { PracticeScheduleEditor } from "@/components/professional/practice-schedule-editor";
import { ProfessionalPortal } from "@/components/professional/professional-portal";

export default function ProfessionalDashboardPage() {
  return (
    <ProfessionalPortal
      mode="dashboard"
      verifiedDoctorSlot={
        <div className="space-y-8">
          <ProfessionalActions />
          <PracticeScheduleEditor />
        </div>
      }
    />
  );
}

function ProfessionalActions() {
  return (
    <section aria-labelledby="today-actions-title">
      <h2 className="text-2xl font-bold tracking-[-0.04em] text-slate-950" id="today-actions-title">
        Today&rsquo;s clinical work
      </h2>
      <div className="mt-4 divide-y divide-slate-200 border-y border-slate-200">
        {[
          {
            description: "Start or resume today’s session, call the next serial, and handle queue exceptions.",
            href: "/professional/chamber",
            icon: QueueListIcon,
            title: "Chamber queue",
          },
          {
            description: "Open the current patient chart, draft clinical notes, prescribe, and finish the visit.",
            href: "/professional/visits",
            icon: ChatBubbleBottomCenterTextIcon,
            title: "Consultation workspace",
          },
        ].map(({ description, href, icon: Icon, title }) => (
          <Link className="group flex items-center gap-4 py-5 sm:px-2" href={href} key={href}>
            <span className="flex size-12 shrink-0 items-center justify-center rounded-full bg-sky-50 text-sky-700 ring-1 ring-inset ring-sky-100">
              <Icon aria-hidden="true" className="size-6" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-base font-semibold text-slate-950">{title}</span>
              <span className="mt-1 block text-sm leading-6 text-slate-600">{description}</span>
            </span>
            <ArrowRightIcon aria-hidden="true" className="size-5 text-sky-700 transition group-hover:translate-x-1" />
          </Link>
        ))}
      </div>
    </section>
  );
}
