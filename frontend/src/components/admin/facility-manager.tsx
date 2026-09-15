"use client";

import { CheckBadgeIcon, MapPinIcon } from "@heroicons/react/24/outline";
import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";

import { AdminPortalGuard } from "@/components/admin/admin-portal-guard";
import { AdminSectionHeader } from "@/components/admin/admin-section-header";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/async-state";
import { confirmFacilityLocation, createFacility, loadFacilities, updateFacility } from "@/lib/admin/api";
import type { Facility, FacilityType, FacilityWriteRequest } from "@/lib/admin/types";
import { citizenErrorMessage } from "@/lib/citizen/presentation";
import { loadBangladeshAreas } from "@/lib/locations/api";
import type { BangladeshAreaOptions } from "@/lib/locations/types";

const emptyForm: FacilityWriteRequest = { name: "", facility_type: "HOSPITAL", registration_number: null, address: "", district_code: null, upazila_code: null, phone: null, email: null, is_active: true };
const inputClass = "mt-2 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm text-slate-950 outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-100";

function FacilityManagerContent() {
  const [facilities, setFacilities] = useState<Facility[] | null>(null);
  const [areas, setAreas] = useState<BangladeshAreaOptions | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [form, setForm] = useState<FacilityWriteRequest>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const [message, setMessage] = useState<{ text: string; tone: "success" | "error" } | null>(null);
  const [query, setQuery] = useState("");
  const formTitleRef = useRef<HTMLHeadingElement>(null);

  const reload = useCallback(async () => {
    try {
      const rows = await loadFacilities();
      setLoadError(null);
      setFacilities(rows);
      return rows;
    } catch (reason) {
      setLoadError(citizenErrorMessage(reason, "We could not load facilities."));
      return null;
    }
  }, []);

  useEffect(() => {
    let active = true;
    void Promise.all([loadFacilities(), loadBangladeshAreas()]).then(
      ([facilityRows, areaRows]) => {
        if (!active) return;
        setLoadError(null);
        setFacilities(facilityRows);
        setAreas(areaRows);
      },
      (reason: unknown) => {
        if (active) setLoadError(citizenErrorMessage(reason, "We could not load the facility registry."));
      },
    );
    return () => { active = false; };
  }, []);

  const upazilas = useMemo(() => areas?.upazilas.filter((item) => item.district_code === form.district_code) ?? [], [areas, form.district_code]);
  const areaLabel = useCallback((facility: Facility) => {
    const district = areas?.districts.find((item) => item.code === facility.district_code);
    const upazila = areas?.upazilas.find((item) => item.code === facility.upazila_code);
    return district && upazila ? `${upazila.name}, ${district.name}` : "Area not selected";
  }, [areas]);
  const setField = <K extends keyof FacilityWriteRequest>(key: K, value: FacilityWriteRequest[K]) => setForm((current) => ({ ...current, [key]: value }));

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setMessage(null);
    if (!form.district_code || !form.upazila_code) {
      setMessage({ text: "Select the facility's zila and upazila.", tone: "error" });
      return;
    }
    setSaving(true);
    const payload = { ...form, name: form.name.trim(), address: form.address.trim(), registration_number: form.registration_number?.trim() || null, phone: form.phone?.trim() || null, email: form.email?.trim() || null };
    try {
      const saved = editingId ? await updateFacility(editingId, payload) : await createFacility(payload);
      setEditingId(saved.id);
      setForm(payload);
      await reload();
      setMessage({ text: saved.location_status === "CONFIRMED" ? "Facility updated. Its confirmed location is unchanged." : "Facility saved. Confirm the address below to enable nearby search.", tone: "success" });
    } catch (reason) {
      setMessage({ text: citizenErrorMessage(reason, "We could not save this facility."), tone: "error" });
    } finally {
      setSaving(false);
    }
  };

  const edit = (facility: Facility) => {
    setEditingId(facility.id);
    setForm({ name: facility.name, facility_type: facility.facility_type, registration_number: facility.registration_number, address: facility.address, district_code: facility.district_code, upazila_code: facility.upazila_code, phone: facility.phone, email: facility.email, is_active: facility.is_active });
    setMessage(null);
    window.setTimeout(() => formTitleRef.current?.focus(), 0);
  };

  const confirmLocation = async (facility: Facility) => {
    setConfirmingId(facility.id);
    setMessage(null);
    try {
      const confirmed = await confirmFacilityLocation(facility.id);
      setFacilities((current) => current?.map((item) => item.id === confirmed.id ? confirmed : item) ?? null);
      setMessage({ text: "Location confirmed. This facility can now be used for nearby search.", tone: "success" });
    } catch (reason) {
      setMessage({ text: citizenErrorMessage(reason, "We could not confirm this address."), tone: "error" });
    } finally {
      setConfirmingId(null);
    }
  };

  const visibleFacilities = facilities?.filter((facility) => `${facility.name} ${facility.address} ${facility.registration_number ?? ""}`.toLowerCase().includes(query.trim().toLowerCase())) ?? null;
  const editingFacility = facilities?.find((item) => item.id === editingId) ?? null;

  return <main className="hl-page" id="main-content">
    <AdminSectionHeader eyebrow="Facility registry" title="Healthcare facilities" description="Maintain trusted facility details and privately confirm their location for nearby doctor search." />
    <div className="mt-8 grid gap-7 lg:grid-cols-[0.9fr_1.1fr]">
      <section className="hl-card p-5 sm:p-7">
        <h2 className="text-xl font-bold text-slate-950 outline-none" ref={formTitleRef} tabIndex={-1}>{editingId ? "Edit facility" : "Create facility"}</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">Choose the registered area and enter the full address. Location details are handled privately by HealthLink.</p>
        <form className="mt-5 grid gap-4" onSubmit={submit}>
          <label className="text-sm font-bold text-slate-700">Name<input className={inputClass} maxLength={200} onChange={(event) => setField("name", event.target.value)} required value={form.name} /></label>
          <label className="text-sm font-bold text-slate-700">Facility type<select className={inputClass} onChange={(event) => setField("facility_type", event.target.value as FacilityType)} value={form.facility_type}><option value="HOSPITAL">Hospital</option><option value="CLINIC">Clinic</option><option value="DIAGNOSTIC_CENTER">Diagnostic Center</option><option value="PHARMACY">Pharmacy</option></select></label>
          <label className="text-sm font-bold text-slate-700">Registration number <span className="font-normal text-slate-500">(optional)</span><input className={inputClass} maxLength={100} onChange={(event) => setField("registration_number", event.target.value)} value={form.registration_number ?? ""} /></label>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="text-sm font-bold text-slate-700">Zila<select className={inputClass} onChange={(event) => setForm((current) => ({ ...current, district_code: event.target.value || null, upazila_code: null }))} required value={form.district_code ?? ""}><option value="">Select zila</option>{areas?.districts.map((item) => <option key={item.code} value={item.code}>{item.name} — {item.name_bn}</option>)}</select></label>
            <label className="text-sm font-bold text-slate-700">Upazila<select className={inputClass} disabled={!form.district_code} onChange={(event) => setField("upazila_code", event.target.value || null)} required value={form.upazila_code ?? ""}><option value="">Select upazila</option>{upazilas.map((item) => <option key={item.code} value={item.code}>{item.name} — {item.name_bn}</option>)}</select></label>
          </div>
          <label className="text-sm font-bold text-slate-700">Registration address<textarea className={`${inputClass} min-h-24 py-3`} onChange={(event) => setField("address", event.target.value)} required value={form.address} /></label>
          <div className="grid gap-4 sm:grid-cols-2"><label className="text-sm font-bold text-slate-700">Phone <span className="font-normal text-slate-500">(optional)</span><input className={inputClass} maxLength={32} onChange={(event) => setField("phone", event.target.value)} value={form.phone ?? ""} /></label><label className="text-sm font-bold text-slate-700">Email <span className="font-normal text-slate-500">(optional)</span><input className={inputClass} maxLength={320} onChange={(event) => setField("email", event.target.value)} type="email" value={form.email ?? ""} /></label></div>
          <label className="flex min-h-11 items-center gap-3 text-sm font-bold text-slate-700"><input checked={form.is_active} onChange={(event) => setField("is_active", event.target.checked)} type="checkbox" />Active and available for verification</label>
          {message ? <p aria-live="polite" role={message.tone === "error" ? "alert" : "status"} className={`rounded-xl p-3 text-sm ${message.tone === "error" ? "bg-rose-50 text-rose-800" : "bg-emerald-50 text-emerald-800"}`}>{message.text}</p> : null}
          <div className="flex flex-wrap gap-3"><button className="min-h-11 rounded-xl bg-indigo-700 px-5 text-sm font-bold text-white disabled:opacity-60" disabled={saving} type="submit">{saving ? "Saving…" : editingId ? "Save changes" : "Create facility"}</button>{editingId ? <button className="min-h-11 rounded-xl border border-slate-300 px-5 text-sm font-bold" onClick={() => { setEditingId(null); setForm(emptyForm); setMessage(null); }} type="button">Finish editing</button> : null}</div>
        </form>
        {editingFacility?.location_status === "PENDING" ? <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 p-4"><div className="flex items-start gap-3"><MapPinIcon aria-hidden="true" className="mt-0.5 size-6 shrink-0 text-amber-700" /><div><h3 className="font-bold text-amber-950">Confirm this facility location</h3><p className="mt-1 text-sm leading-6 text-amber-900">HealthLink will privately match the registration address. No coordinate values are displayed or added to the form.</p><button className="mt-3 min-h-11 rounded-xl bg-amber-700 px-4 text-sm font-bold text-white disabled:opacity-60" disabled={confirmingId === editingFacility.id} onClick={() => void confirmLocation(editingFacility)} type="button">{confirmingId === editingFacility.id ? "Matching address…" : "Confirm registered address"}</button><p className="mt-3 text-xs text-amber-800">Address matching © OpenStreetMap contributors.</p></div></div></div> : null}
      </section>
      <section aria-label="Registered facilities"><label className="mb-4 block text-sm font-bold text-slate-700">Search facilities<input className={inputClass} placeholder="Name, address, or registration number" value={query} onChange={(event) => setQuery(event.target.value)} /></label>
        {facilities === null && !loadError ? <LoadingState description="Loading the trusted facility registry." label="Loading facilities" /> : null}
        {loadError ? <ErrorState message={loadError} onAction={() => { setLoadError(null); setFacilities(null); void reload(); }} title="Facilities unavailable" /> : null}
        {visibleFacilities?.length === 0 ? <EmptyState message="Create the first facility before verifying a professional." title="No facilities yet" /> : null}
        <div className="grid gap-4">{visibleFacilities?.map((facility) => <article className="rounded-[1.4rem] border border-slate-200 bg-white p-5 shadow-sm" key={facility.id}><div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between"><div><div className="flex flex-wrap items-center gap-2"><h2 className="text-lg font-bold text-slate-950">{facility.name}</h2><span className={`rounded-full px-2.5 py-1 text-xs font-bold ${facility.is_active ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-600"}`}>{facility.is_active ? "Active" : "Inactive"}</span><span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-bold ${facility.location_status === "CONFIRMED" ? "bg-sky-50 text-sky-800" : "bg-amber-50 text-amber-800"}`}>{facility.location_status === "CONFIRMED" ? <CheckBadgeIcon aria-hidden="true" className="size-4" /> : <MapPinIcon aria-hidden="true" className="size-4" />}{facility.location_status === "CONFIRMED" ? "Location confirmed" : "Needs location confirmation"}</span></div><p className="mt-2 text-sm text-slate-600">{facility.facility_type.replaceAll("_", " ")} · {areaLabel(facility)}</p><p className="mt-1 text-sm text-slate-600">{facility.address}</p>{facility.registration_number ? <p className="mt-1 text-xs text-slate-500">Registration: {facility.registration_number}</p> : null}{facility.location_matched_address ? <p className="mt-2 text-xs leading-5 text-slate-500">Matched address: {facility.location_matched_address}</p> : null}</div><div className="flex shrink-0 flex-wrap gap-2"><button className="min-h-11 rounded-xl border border-slate-300 px-4 text-sm font-bold text-slate-700" onClick={() => edit(facility)} type="button">Edit</button>{facility.location_status === "PENDING" && facility.district_code && facility.upazila_code ? <button className="min-h-11 rounded-xl bg-indigo-700 px-4 text-sm font-bold text-white disabled:opacity-60" disabled={confirmingId === facility.id} onClick={() => void confirmLocation(facility)} type="button">{confirmingId === facility.id ? "Matching…" : "Confirm location"}</button> : null}</div></div></article>)}</div>
      </section>
    </div>
  </main>;
}

export function FacilityManager() {
  return <AdminPortalGuard><FacilityManagerContent /></AdminPortalGuard>;
}
