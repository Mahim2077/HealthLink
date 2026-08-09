"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

import { AdminPortalGuard } from "@/components/admin/admin-portal-guard";
import { AdminSectionHeader } from "@/components/admin/admin-section-header";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/async-state";
import { createFacility, loadFacilities, updateFacility } from "@/lib/admin/api";
import type { Facility, FacilityType, FacilityWriteRequest } from "@/lib/admin/types";
import { citizenErrorMessage } from "@/lib/citizen/presentation";


const emptyForm: FacilityWriteRequest = { name: "", facility_type: "HOSPITAL", registration_number: null, address: "", phone: null, email: null, is_active: true };
const inputClass = "mt-2 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm text-slate-950 outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-100";

function FacilityManagerContent() {
  const [facilities, setFacilities] = useState<Facility[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [form, setForm] = useState<FacilityWriteRequest>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try { const rows = await loadFacilities(); setLoadError(null); setFacilities(rows); }
    catch (reason) { setLoadError(citizenErrorMessage(reason, "We could not load facilities.")); }
  }, []);
  useEffect(() => {
    let active = true;
    void loadFacilities().then(
      (rows) => { if (active) { setLoadError(null); setFacilities(rows); } },
      (reason: unknown) => { if (active) setLoadError(citizenErrorMessage(reason, "We could not load facilities.")); },
    );
    return () => { active = false; };
  }, []);

  const setField = <K extends keyof FacilityWriteRequest>(key: K, value: FacilityWriteRequest[K]) => setForm((current) => ({ ...current, [key]: value }));
  const submit = async (event: FormEvent) => {
    event.preventDefault(); setSaving(true); setMessage(null);
    const payload = { ...form, name: form.name.trim(), address: form.address.trim(), registration_number: form.registration_number?.trim() || null, phone: form.phone?.trim() || null, email: form.email?.trim() || null };
    try {
      if (editingId) await updateFacility(editingId, payload); else await createFacility(payload);
      setMessage(editingId ? "Facility updated." : "Facility created.");
      setEditingId(null); setForm(emptyForm); await reload();
    } catch (reason) { setMessage(citizenErrorMessage(reason, "We could not save this facility.")); }
    finally { setSaving(false); }
  };
  const edit = (facility: Facility) => {
    setEditingId(facility.id);
    setForm({ name: facility.name, facility_type: facility.facility_type, registration_number: facility.registration_number, address: facility.address, phone: facility.phone, email: facility.email, is_active: facility.is_active });
    setMessage(null);
  };

  return <main className="mx-auto w-full max-w-7xl flex-1 px-5 py-10 sm:px-8 lg:px-10" id="main-content">
    <AdminSectionHeader eyebrow="Facility registry" title="Healthcare facilities" description="Create and maintain the trusted facilities that professional applications can be matched to during verification." />
    <div className="mt-8 grid gap-7 lg:grid-cols-[0.9fr_1.1fr]">
      <section className="rounded-[1.5rem] border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
        <h2 className="text-xl font-bold text-slate-950">{editingId ? "Edit facility" : "Create facility"}</h2>
        <form className="mt-5 grid gap-4" onSubmit={submit}>
          <label className="text-sm font-bold text-slate-700">Name<input className={inputClass} maxLength={200} onChange={(event) => setField("name", event.target.value)} required value={form.name} /></label>
          <label className="text-sm font-bold text-slate-700">Facility type<select className={inputClass} onChange={(event) => setField("facility_type", event.target.value as FacilityType)} value={form.facility_type}><option value="HOSPITAL">Hospital</option><option value="CLINIC">Clinic</option><option value="DIAGNOSTIC_CENTER">Diagnostic Center</option><option value="PHARMACY">Pharmacy</option></select></label>
          <label className="text-sm font-bold text-slate-700">Registration number <span className="font-normal text-slate-500">(optional)</span><input className={inputClass} maxLength={100} onChange={(event) => setField("registration_number", event.target.value)} value={form.registration_number ?? ""} /></label>
          <label className="text-sm font-bold text-slate-700">Address<textarea className={`${inputClass} min-h-24 py-3`} onChange={(event) => setField("address", event.target.value)} required value={form.address} /></label>
          <div className="grid gap-4 sm:grid-cols-2"><label className="text-sm font-bold text-slate-700">Phone <span className="font-normal text-slate-500">(optional)</span><input className={inputClass} maxLength={32} onChange={(event) => setField("phone", event.target.value)} value={form.phone ?? ""} /></label><label className="text-sm font-bold text-slate-700">Email <span className="font-normal text-slate-500">(optional)</span><input className={inputClass} maxLength={320} onChange={(event) => setField("email", event.target.value)} type="email" value={form.email ?? ""} /></label></div>
          <label className="flex min-h-11 items-center gap-3 text-sm font-bold text-slate-700"><input checked={form.is_active} onChange={(event) => setField("is_active", event.target.checked)} type="checkbox" />Active and available for verification</label>
          {message ? <p aria-live="polite" className="rounded-xl bg-indigo-50 p-3 text-sm text-indigo-950">{message}</p> : null}
          <div className="flex flex-wrap gap-3"><button className="min-h-11 rounded-xl bg-indigo-700 px-5 text-sm font-bold text-white disabled:opacity-60" disabled={saving} type="submit">{saving ? "Saving…" : editingId ? "Save changes" : "Create facility"}</button>{editingId ? <button className="min-h-11 rounded-xl border border-slate-300 px-5 text-sm font-bold" onClick={() => { setEditingId(null); setForm(emptyForm); }} type="button">Cancel</button> : null}</div>
        </form>
      </section>
      <section aria-label="Registered facilities">
        {facilities === null && !loadError ? <LoadingState description="Loading the trusted facility registry." label="Loading facilities" /> : null}
        {loadError ? <ErrorState message={loadError} onAction={() => { setLoadError(null); setFacilities(null); void reload(); }} title="Facilities unavailable" /> : null}
        {facilities?.length === 0 ? <EmptyState message="Create the first facility before verifying a professional." title="No facilities yet" /> : null}
        <div className="grid gap-4">{facilities?.map((facility) => <article className="rounded-[1.4rem] border border-slate-200 bg-white p-5 shadow-sm" key={facility.id}><div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between"><div><div className="flex flex-wrap items-center gap-2"><h2 className="text-lg font-bold text-slate-950">{facility.name}</h2><span className={`rounded-full px-2.5 py-1 text-xs font-bold ${facility.is_active ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-600"}`}>{facility.is_active ? "ACTIVE" : "INACTIVE"}</span></div><p className="mt-2 text-sm text-slate-600">{facility.facility_type.replaceAll("_", " ")} · {facility.address}</p>{facility.registration_number ? <p className="mt-1 text-xs text-slate-500">Registration: {facility.registration_number}</p> : null}</div><button className="min-h-11 rounded-xl border border-slate-300 px-4 text-sm font-bold text-slate-700" onClick={() => edit(facility)} type="button">Edit</button></div></article>)}</div>
      </section>
    </div>
  </main>;
}

export function FacilityManager() {
  return <AdminPortalGuard><FacilityManagerContent /></AdminPortalGuard>;
}
