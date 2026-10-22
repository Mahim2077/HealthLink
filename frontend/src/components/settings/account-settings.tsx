"use client";

import Link from "next/link";
import { CitizenProfileManager } from "@/components/citizen/citizen-profile-manager";
import { useSettingsContext } from "./settings-layout";

export function AccountSettings() {
  const { portal, professional, admin } = useSettingsContext();
  if (portal === "CITIZEN") return <CitizenProfileManager embedded />;
  const record = professional ?? admin;
  if (!record) return null;
  return <section className="hl-settings-card" aria-labelledby="account-title">
    <h2 id="account-title" className="hl-section-title">Your account</h2>
    <p className="hl-section-description">Review the account used in this portal. Protected account and verification details cannot be edited here.</p>
    <dl className="mt-6 grid gap-5 sm:grid-cols-2">
      <div><dt className="hl-setting-help">Name</dt><dd className="mt-1 font-semibold">{record.first_name} {record.last_name}</dd></div>
      <div className="min-w-0"><dt className="hl-setting-help">Email</dt><dd className="mt-1 break-words font-semibold">{record.email}</dd></div>
      {professional ? <>
        <div><dt className="hl-setting-help">Selected professional role</dt><dd className="mt-1 font-semibold">{professional.role_name}</dd></div>
        <div><dt className="hl-setting-help">Verification</dt><dd className="mt-1 font-semibold">{professional.verification_status === "VERIFIED" ? "Verified" : professional.verification_status === "PENDING" ? "Under review" : "Not approved"}</dd></div>
        <div><dt className="hl-setting-help">Designation</dt><dd className="mt-1 font-semibold">{professional.designation}</dd></div>
        <div><dt className="hl-setting-help">Verified facility</dt><dd className="mt-1 font-semibold">{professional.facility?.name ?? "No facility linked"}</dd></div>
      </> : <div><dt className="hl-setting-help">Account role</dt><dd className="mt-1 font-semibold">{admin?.is_super_admin ? "Super administrator" : "Administrator"}</dd></div>}
    </dl>
    {professional ? <Link href="/professional/status" className="hl-button-secondary mt-6">View verification details</Link> : null}
    <p className="mt-6 rounded-xl bg-slate-50 p-4 text-sm leading-6 text-slate-600">{professional ? "Role approvals and facility assignments are managed by administrators. Sign out and select another approved role to change your professional workspace." : "Operational tools such as facilities, verification and citizen identity support remain in the admin workspace."}</p>
  </section>;
}
