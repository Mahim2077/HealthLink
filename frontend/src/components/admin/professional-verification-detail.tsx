"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import { AdminPortalGuard } from "@/components/admin/admin-portal-guard";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/async-state";
import { loadFacilities, loadProfessionalRegistration, rejectProfessionalRegistration, verifyProfessionalRegistration } from "@/lib/admin/api";
import type { Facility, ProfessionalRegistrationDetail } from "@/lib/admin/types";
import { citizenErrorMessage } from "@/lib/citizen/presentation";


function ProfessionalVerificationDetailContent({ registrationId }: { registrationId: string }) {
  const [registration, setRegistration] = useState<ProfessionalRegistrationDetail | null>(null);
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [facilityId, setFacilityId] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const load = useCallback(async () => {
    try {
      const [detail, facilityRows] = await Promise.all([loadProfessionalRegistration(registrationId), loadFacilities()]);
      setError(null); setRegistration(detail); setFacilities(facilityRows);
      setFacilityId(detail.facility?.id ?? facilityRows.find((item) => item.is_active)?.id ?? "");
    } catch (cause) { setError(citizenErrorMessage(cause, "We could not load this application.")); }
  }, [registrationId]);
  useEffect(() => {
    let active = true;
    void Promise.all([loadProfessionalRegistration(registrationId), loadFacilities()]).then(
      ([detail, facilityRows]) => {
        if (active) {
          setError(null); setRegistration(detail); setFacilities(facilityRows);
          setFacilityId(detail.facility?.id ?? facilityRows.find((item) => item.is_active)?.id ?? "");
        }
      },
      (cause: unknown) => { if (active) setError(citizenErrorMessage(cause, "We could not load this application.")); },
    );
    return () => { active = false; };
  }, [registrationId]);

  const verify = async (event: FormEvent) => {
    event.preventDefault(); if (!facilityId) { setActionError("Select an active facility before verification."); return; }
    setSaving(true); setActionError(null);
    try { setRegistration(await verifyProfessionalRegistration(registrationId, facilityId)); }
    catch (cause) { setActionError(citizenErrorMessage(cause, "We could not verify this application.")); }
    finally { setSaving(false); }
  };
  const reject = async (event: FormEvent) => {
    event.preventDefault(); const trimmed = reason.trim();
    if (!trimmed) { setActionError("A rejection reason is required."); return; }
    setSaving(true); setActionError(null);
    try { setRegistration(await rejectProfessionalRegistration(registrationId, trimmed)); }
    catch (cause) { setActionError(citizenErrorMessage(cause, "We could not reject this application.")); }
    finally { setSaving(false); }
  };

  return <main className="mx-auto w-full max-w-6xl flex-1 px-5 py-10 sm:px-8 lg:px-10" id="main-content">
    <Link className="text-sm font-bold text-indigo-700" href="/admin/professional-registrations">← Verification queue</Link>
    {!registration && !error ? <div className="mt-8"><LoadingState description="Loading role-specific application evidence." label="Loading application" /></div> : null}
    {error ? <div className="mt-8"><ErrorState message={error} onAction={() => { setError(null); void load(); }} title="Application unavailable" /></div> : null}
    {registration ? <>
      <header className="mt-7 border-b border-slate-200 pb-7"><div className="flex flex-wrap items-center gap-3"><p className="text-xs font-bold uppercase tracking-[0.15em] text-indigo-700">{registration.role_name}</p><span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-700">{registration.verification_status}</span></div><h1 className="mt-3 font-display text-3xl font-bold tracking-[-0.04em] text-slate-950">{registration.first_name} {registration.last_name}</h1><p className="mt-2 text-sm text-slate-600">{registration.email}</p></header>
      <div className="mt-7 grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
        <section className="rounded-[1.5rem] border border-slate-200 bg-white p-6 shadow-sm"><h2 className="text-xl font-bold text-slate-950">Submitted evidence</h2><dl className="mt-5 grid gap-4"><div><dt className="text-xs font-bold uppercase tracking-wide text-slate-500">Requested role</dt><dd className="mt-1 text-sm font-semibold text-slate-950">{registration.role_name}</dd></div><div><dt className="text-xs font-bold uppercase tracking-wide text-slate-500">Designation</dt><dd className="mt-1 text-sm text-slate-800">{registration.designation}</dd></div><div><dt className="text-xs font-bold uppercase tracking-wide text-slate-500">Submitted facility</dt><dd className="mt-1 text-sm text-slate-800">{registration.facility_name_submitted}</dd></div>{registration.role_code === "DOCTOR" ? <div className="rounded-xl border border-indigo-100 bg-indigo-50 p-4"><dt className="text-xs font-bold uppercase tracking-wide text-indigo-700">BM&amp;DC registration number</dt><dd className="mt-1 break-words text-base font-bold text-indigo-950">{registration.bmdc_registration_number}</dd></div> : null}<div><dt className="text-xs font-bold uppercase tracking-wide text-slate-500">Additional information</dt><dd className="mt-1 whitespace-pre-wrap text-sm leading-6 text-slate-800">{registration.additional_info ?? "Not provided"}</dd></div></dl></section>
        <section className="rounded-[1.5rem] border border-slate-200 bg-white p-6 shadow-sm"><h2 className="text-xl font-bold text-slate-950">Admin decision</h2>{registration.verification_status === "PENDING" ? <div className="mt-5 grid gap-6"><form onSubmit={verify}><label className="text-sm font-bold text-slate-700">Match active facility<select className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm" onChange={(event) => setFacilityId(event.target.value)} required value={facilityId}><option value="">Select a facility</option>{facilities.filter((item) => item.is_active).map((item) => <option key={item.id} value={item.id}>{item.name} · {item.facility_type.replaceAll("_", " ")}</option>)}</select></label>{facilities.every((item) => !item.is_active) ? <p className="mt-3 text-sm text-amber-800">No active facility is available. <Link className="font-bold underline" href="/admin/facilities">Create or activate one</Link>.</p> : null}<button className="mt-4 min-h-11 w-full rounded-xl bg-emerald-700 px-5 text-sm font-bold text-white disabled:opacity-60" disabled={saving || !facilityId} type="submit">Verify and link facility</button></form><div className="border-t border-slate-200" /><form onSubmit={reject}><label className="text-sm font-bold text-slate-700">Rejection reason<textarea className="mt-2 min-h-28 w-full rounded-xl border border-slate-300 p-3 text-sm" onChange={(event) => setReason(event.target.value)} required value={reason} /></label><button className="mt-4 min-h-11 w-full rounded-xl border border-rose-300 bg-rose-50 px-5 text-sm font-bold text-rose-800 disabled:opacity-60" disabled={saving} type="submit">Reject application</button></form>{actionError ? <p aria-live="assertive" className="rounded-xl bg-rose-50 p-3 text-sm text-rose-800">{actionError}</p> : null}</div> : <div className="mt-5"><EmptyState message={registration.verification_status === "VERIFIED" ? `Linked to ${registration.facility?.name ?? "the selected facility"}.` : registration.rejection_reason ?? "This application was rejected."} title={`Decision recorded: ${registration.verification_status}`} /></div>}</section>
      </div>
    </> : null}
  </main>;
}

export function ProfessionalVerificationDetail({ registrationId }: { registrationId: string }) {
  return <AdminPortalGuard><ProfessionalVerificationDetailContent registrationId={registrationId} /></AdminPortalGuard>;
}
