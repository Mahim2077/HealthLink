"use client";

import {
  CheckBadgeIcon,
  ClipboardDocumentCheckIcon,
  HeartIcon,
  MagnifyingGlassIcon,
  MapPinIcon,
  SparklesIcon,
  UserCircleIcon,
  UserGroupIcon,
  WrenchScrewdriverIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";

import { usePortalAuth } from "@/components/auth/auth-provider";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/async-state";
import { citizenErrorMessage } from "@/lib/citizen/presentation";
import { loadDoctorDiscoveryFacilities, searchDoctors } from "@/lib/doctors/api";
import type {
  DoctorDiscoveryFacility,
  DoctorSearchFilters,
  DoctorSearchResponse,
  DoctorSort,
  DoctorSummary,
  PracticeWeekday,
} from "@/lib/doctors/types";
import type { DoctorSpecialization } from "@/lib/doctors/specializations";
import { loadBangladeshAreas } from "@/lib/locations/api";
import type { BangladeshAreaOptions } from "@/lib/locations/types";

const WEEKDAY_LABEL: Record<PracticeWeekday, string> = { MONDAY: "Monday", TUESDAY: "Tuesday", WEDNESDAY: "Wednesday", THURSDAY: "Thursday", FRIDAY: "Friday", SATURDAY: "Saturday", SUNDAY: "Sunday" };
const SORT_OPTIONS: { value: DoctorSort; label: string }[] = [
  { value: "BEST_MATCH", label: "Best match" },
  { value: "EARLIEST_PRACTICE", label: "Earliest practice window" },
  { value: "NEAREST", label: "Nearest facility" },
  { value: "DOCTOR_NAME", label: "Doctor name A–Z" },
  { value: "FACILITY_NAME", label: "Facility name A–Z" },
];
const FEATURED_SPECIALTIES: { code: DoctorSpecialization; label: string; icon: typeof HeartIcon }[] = [
  { code: "PEDIATRICS", label: "Pediatrics", icon: UserGroupIcon },
  { code: "ORTHOPEDICS", label: "Orthopedics", icon: WrenchScrewdriverIcon },
  { code: "CARDIOLOGY", label: "Cardiology", icon: HeartIcon },
  { code: "GYNECOLOGY_OBSTETRICS", label: "Gynecology", icon: UserCircleIcon },
  { code: "DERMATOLOGY", label: "Dermatology", icon: SparklesIcon },
  { code: "GENERAL_MEDICINE", label: "General Medicine", icon: ClipboardDocumentCheckIcon },
];

function dhakaWeekday(offset: number): PracticeWeekday {
  const parts = new Intl.DateTimeFormat("en-US", { timeZone: "Asia/Dhaka", weekday: "long" }).formatToParts(new Date(Date.now() + offset * 86_400_000));
  return parts.find((item) => item.type === "weekday")!.value.toUpperCase() as PracticeWeekday;
}

function timeLabel(value: string): string {
  const [hourValue, minute] = value.split(":");
  const hour = Number(hourValue);
  return `${hour % 12 || 12}:${minute} ${hour >= 12 ? "PM" : "AM"}`;
}

function nextPracticeLabel(doctor: DoctorSummary): string {
  const practice = doctor.next_practice;
  if (!practice) return "Schedule not published";
  const day = practice.days_away === 0 ? "Today" : practice.days_away === 1 ? "Tomorrow" : WEEKDAY_LABEL[practice.weekday];
  return `${day}, ${timeLabel(practice.start_time)}–${timeLabel(practice.end_time)}`;
}

function distanceLabel(distanceKm: number | null): string {
  if (distanceKm === null) return "";
  if (distanceKm < 1) return " · Less than 1 km away";
  return ` · About ${distanceKm} km away`;
}

function DoctorResult({ doctor }: { doctor: DoctorSummary }) {
  return <article className="grid gap-4 border-b border-slate-200 px-4 py-5 last:border-b-0 sm:px-5 lg:grid-cols-[1.15fr_0.9fr_0.9fr_1.1fr_auto] lg:items-center" data-testid="doctor-row">
    <div className="flex min-w-0 items-center gap-3">
      <span className="flex size-11 shrink-0 items-center justify-center rounded-full bg-teal-50 text-teal-700"><UserCircleIcon aria-hidden="true" className="size-7" /></span>
      <div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><h2 className="font-bold text-slate-950">{doctor.name}</h2>{doctor.verified ? <span className="inline-flex items-center gap-1 rounded-full bg-teal-50 px-2 py-1 text-[0.68rem] font-bold text-teal-800"><CheckBadgeIcon aria-hidden="true" className="size-3.5" />Verified</span> : null}</div><p className="mt-1 text-sm text-slate-500">{doctor.designation}</p></div>
    </div>
    <div><p className="text-xs font-bold uppercase tracking-wide text-slate-400 lg:hidden">Specialty</p><p className="text-sm font-bold text-slate-800">{doctor.specialization}</p>{doctor.qualification ? <p className="mt-1 text-xs leading-5 text-slate-500">{doctor.qualification}</p> : null}</div>
    <div><p className="text-xs font-bold uppercase tracking-wide text-slate-400 lg:hidden">Facility</p><p className="text-sm font-semibold text-slate-800">{doctor.facility_name}</p><p className="mt-1 text-xs text-slate-500">{doctor.facility_area ?? doctor.facility_type.replaceAll("_", " ")}{distanceLabel(doctor.distance_km)}</p></div>
    <div><p className="text-xs font-bold uppercase tracking-wide text-slate-400 lg:hidden">Next practice</p><p className="text-xs font-bold text-teal-700">Next practice</p><p className="mt-1 text-sm font-semibold text-slate-700">{nextPracticeLabel(doctor)}</p></div>
    <div className="flex flex-wrap gap-2 lg:justify-end"><Link className="inline-flex min-h-10 items-center justify-center rounded-xl border border-teal-700 px-4 text-sm font-bold text-teal-800 hover:bg-teal-50" href={`/citizen/doctors/${doctor.id}`}>View profile</Link><Link className="inline-flex min-h-10 items-center justify-center rounded-xl bg-teal-700 px-4 text-sm font-bold text-white hover:bg-teal-800" href={`/citizen/appointments/book?doctor_user_id=${encodeURIComponent(doctor.id)}`}>Book appointment</Link></div>
  </article>;
}

function LocationDialog({ areas, onClose, onGps, onManual, locating }: { areas: BangladeshAreaOptions | null; onClose: () => void; onGps: () => void; onManual: (districtCode: string, upazilaCode: string, label: string) => void; locating: boolean }) {
  const [manual, setManual] = useState(false);
  const [districtCode, setDistrictCode] = useState("");
  const [upazilaCode, setUpazilaCode] = useState("");
  const closeRef = useRef<HTMLButtonElement>(null);
  const upazilas = useMemo(() => areas?.upazilas.filter((item) => item.district_code === districtCode) ?? [], [areas, districtCode]);

  useEffect(() => {
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  const submitManual = (event: FormEvent) => {
    event.preventDefault();
    const district = areas?.districts.find((item) => item.code === districtCode);
    const upazila = areas?.upazilas.find((item) => item.code === upazilaCode);
    if (district && upazila) onManual(district.code, upazila.code, `${upazila.name}, ${district.name}`);
  };

  return <div className="fixed inset-0 z-[70] flex items-center justify-center bg-slate-950/45 p-4 backdrop-blur-[2px]" role="presentation">
    <section aria-labelledby="location-title" aria-modal="true" className="relative w-full max-w-lg rounded-[1.5rem] bg-white p-6 text-center shadow-2xl sm:p-8" role="dialog">
      <button aria-label="Close location choice" className="absolute right-4 top-4 flex size-10 items-center justify-center rounded-full text-slate-500 hover:bg-slate-100" onClick={onClose} ref={closeRef} type="button"><XMarkIcon aria-hidden="true" className="size-6" /></button>
      <span className="mx-auto flex size-20 items-center justify-center rounded-full bg-teal-50 text-teal-700"><MapPinIcon aria-hidden="true" className="size-11" /></span>
      <h2 className="mt-5 font-display text-2xl font-bold tracking-tight text-slate-950" id="location-title">{manual ? "Choose your area" : "Use your approximate location?"}</h2>
      {!manual ? <><p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-600">HealthLink uses your location once to sort nearby healthcare facilities. Your precise location is not stored.</p><div className="mt-6 grid gap-3"><button className="min-h-12 rounded-xl bg-teal-700 px-5 text-sm font-bold text-white hover:bg-teal-800 disabled:opacity-60" disabled={locating} onClick={onGps} type="button">{locating ? "Finding nearby facilities…" : "Use approximate location"}</button><button className="min-h-12 rounded-xl border border-teal-700 px-5 text-sm font-bold text-teal-800 hover:bg-teal-50" onClick={() => setManual(true)} type="button">Enter area manually</button><button className="min-h-11 text-sm font-bold text-teal-700 underline underline-offset-4" onClick={onClose} type="button">Not now</button></div><p className="mt-3 text-xs text-slate-500">You can change this anytime.</p></> : <form className="mt-6 grid gap-4 text-left" onSubmit={submitManual}><label className="text-sm font-bold text-slate-700">Zila<select className="hl-field mt-2" onChange={(event) => { setDistrictCode(event.target.value); setUpazilaCode(""); }} required value={districtCode}><option value="">Select zila</option>{areas?.districts.map((item) => <option key={item.code} value={item.code}>{item.name} — {item.name_bn}</option>)}</select></label><label className="text-sm font-bold text-slate-700">Upazila<select className="hl-field mt-2" disabled={!districtCode} onChange={(event) => setUpazilaCode(event.target.value)} required value={upazilaCode}><option value="">Select upazila</option>{upazilas.map((item) => <option key={item.code} value={item.code}>{item.name} — {item.name_bn}</option>)}</select></label><button className="mt-1 min-h-12 rounded-xl bg-teal-700 px-5 text-sm font-bold text-white disabled:opacity-60" disabled={!upazilaCode} type="submit">Find doctors in this area</button><button className="min-h-10 text-center text-sm font-bold text-teal-700" onClick={() => setManual(false)} type="button">Back to location choices</button></form>}
    </section>
  </div>;
}

function SearchContent({ searchAction }: { searchAction: (filters: DoctorSearchFilters) => Promise<DoctorSearchResponse> }) {
  const [filters, setFilters] = useState<DoctorSearchFilters>({ sort: "BEST_MATCH", limit: 50 });
  const [results, setResults] = useState<DoctorSearchResponse | null>(null);
  const [facilities, setFacilities] = useState<DoctorDiscoveryFacility[]>([]);
  const [areas, setAreas] = useState<BangladeshAreaOptions | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [locationOpen, setLocationOpen] = useState(false);
  const [locating, setLocating] = useState(false);
  const [locationLabel, setLocationLabel] = useState<string | null>(null);
  const locationRef = useRef<{ latitude: number; longitude: number } | null>(null);
  const requestId = useRef(0);

  const runSearch = useCallback(async (next: DoctorSearchFilters) => {
    const id = ++requestId.current;
    setLoading(true);
    setError(null);
    const request = { ...next };
    if (request.sort === "NEAREST" && locationRef.current) Object.assign(request, locationRef.current);
    try {
      const response = await searchAction(request);
      if (requestId.current === id) setResults(response);
    } catch (reason) {
      if (requestId.current === id) setError(citizenErrorMessage(reason, "We could not search doctors right now."));
    } finally {
      if (requestId.current === id) setLoading(false);
    }
  }, [searchAction]);

  useEffect(() => {
    let active = true;
    void Promise.all([loadDoctorDiscoveryFacilities(), loadBangladeshAreas(), searchAction({ sort: "BEST_MATCH", limit: 50 })]).then(
      ([facilityRows, areaRows, response]) => { if (active) { setFacilities(facilityRows); setAreas(areaRows); setResults(response); setLoading(false); } },
      (reason: unknown) => { if (active) { setError(citizenErrorMessage(reason, "We could not load doctor discovery.")); setLoading(false); } },
    );
    return () => { active = false; };
  }, [searchAction]);

  const apply = (next: DoctorSearchFilters) => { setFilters(next); void runSearch(next); };
  const selectSort = (sort: DoctorSort) => {
    if (sort === "NEAREST" && !locationLabel) { setLocationOpen(true); return; }
    apply({ ...filters, sort, offset: 0 });
  };
  const chooseGps = () => {
    if (!navigator.geolocation) { setError("Location is not available in this browser. Choose your area manually instead."); return; }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        locationRef.current = { latitude: Number(position.coords.latitude.toFixed(2)), longitude: Number(position.coords.longitude.toFixed(2)) };
        setLocating(false); setLocationLabel("Approximate location"); setLocationOpen(false);
        const next = { ...filters, sort: "NEAREST" as const, district_code: undefined, upazila_code: undefined, offset: 0 };
        setFilters(next); void runSearch(next);
      },
      () => { setLocating(false); setError("We could not use your location. Choose a zila and upazila instead."); },
      { enableHighAccuracy: false, maximumAge: 0, timeout: 10_000 },
    );
  };
  const chooseManual = (districtCode: string, upazilaCode: string, label: string) => {
    locationRef.current = null;
    setLocationLabel(label); setLocationOpen(false);
    const next = { ...filters, sort: "NEAREST" as const, district_code: districtCode, upazila_code: upazilaCode, offset: 0 };
    setFilters(next); void runSearch(next);
  };
  const clearAll = () => {
    locationRef.current = null; setLocationLabel(null);
    const next: DoctorSearchFilters = { sort: "BEST_MATCH", limit: 50 };
    setFilters(next); void runSearch(next);
  };
  const selectedSpecialty = FEATURED_SPECIALTIES.find((item) => item.code === filters.specialization);
  const selectedFacility = facilities.find((item) => item.id === filters.facility_id);

  return <main className="hl-page !max-w-[92rem]" id="main-content">
    <header><h1 className="font-display text-4xl font-bold tracking-[-0.045em] text-slate-950 sm:text-5xl">Find the right doctor</h1><p className="mt-3 text-base text-slate-600">Search by specialty, doctor name, or hospital to find verified doctors across Bangladesh.</p></header>
    <form className="mt-6 flex flex-col gap-3 sm:flex-row" onSubmit={(event) => { event.preventDefault(); void runSearch({ ...filters, offset: 0 }); }}><label className="relative flex-1"><span className="sr-only">Search doctor, specialty, or hospital</span><MagnifyingGlassIcon aria-hidden="true" className="pointer-events-none absolute left-5 top-1/2 size-6 -translate-y-1/2 text-slate-500" /><input className="min-h-16 w-full rounded-2xl border border-slate-300 bg-white pl-14 pr-5 text-base text-slate-950 shadow-sm outline-none placeholder:text-slate-400 focus:border-teal-700 focus:ring-4 focus:ring-teal-50" maxLength={200} onChange={(event) => setFilters((current) => ({ ...current, query: event.target.value || undefined }))} placeholder="Search doctor, specialty, or hospital" value={filters.query ?? ""} /></label><button className="min-h-14 rounded-xl bg-teal-700 px-9 text-base font-bold text-white hover:bg-teal-800 sm:min-h-16" type="submit">Search</button></form>

    <section className="mt-7" aria-labelledby="specialty-heading"><h2 className="font-display text-2xl font-bold text-slate-950" id="specialty-heading">Browse by specialty</h2><div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">{FEATURED_SPECIALTIES.map((item) => { const Icon = item.icon; const selected = filters.specialization === item.code; return <button aria-pressed={selected} className={`min-h-28 rounded-2xl border bg-white p-4 text-center transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 ${selected ? "border-teal-700 bg-teal-50/60 shadow-sm" : "border-slate-200 hover:border-teal-300"}`} key={item.code} onClick={() => apply({ ...filters, specialization: selected ? undefined : item.code, offset: 0 })} type="button"><span className="mx-auto flex size-12 items-center justify-center rounded-full bg-teal-50 text-teal-700"><Icon aria-hidden="true" className="size-7" /></span><span className="mt-2 block text-sm font-bold text-slate-800">{item.label}</span></button>; })}</div></section>

    <section className="mt-6 grid gap-5 border-b border-slate-200 pb-5 lg:grid-cols-[1.05fr_1fr_0.8fr] lg:items-end"><div><p className="text-sm font-bold text-slate-700">Preferred day</p><div className="mt-2 flex flex-wrap gap-2">{([{ label: "Any day", value: undefined }, { label: "Today", value: dhakaWeekday(0) }, { label: "Tomorrow", value: dhakaWeekday(1) }] as const).map((item) => <button aria-pressed={filters.weekday === item.value || (!filters.weekday && !item.value)} className={`min-h-11 rounded-full border px-5 text-sm font-bold ${filters.weekday === item.value || (!filters.weekday && !item.value) ? "border-teal-600 bg-teal-50 text-teal-800" : "border-slate-300 bg-white text-slate-700"}`} key={item.label} onClick={() => apply({ ...filters, weekday: item.value, offset: 0 })} type="button">{item.label}</button>)}</div></div><label className="text-sm font-bold text-slate-700">Facility<select className="hl-field mt-2" onChange={(event) => apply({ ...filters, facility_id: event.target.value || undefined, offset: 0 })} value={filters.facility_id ?? ""}><option value="">All facilities</option>{facilities.map((item) => <option key={item.id} value={item.id}>{item.name}{item.area ? ` · ${item.area}` : ""}</option>)}</select></label><label className="text-sm font-bold text-slate-700">Sort by<select className="hl-field mt-2" onChange={(event) => selectSort(event.target.value as DoctorSort)} value={filters.sort ?? "BEST_MATCH"}>{SORT_OPTIONS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label></section>

    <div className="mt-4 flex min-h-10 flex-wrap items-center gap-2">{selectedSpecialty ? <button className="inline-flex min-h-9 items-center gap-2 rounded-full bg-teal-50 px-3 text-sm font-bold text-teal-800" onClick={() => apply({ ...filters, specialization: undefined, offset: 0 })} type="button">{selectedSpecialty.label}<XMarkIcon aria-hidden="true" className="size-4" /></button> : null}{filters.weekday ? <button className="inline-flex min-h-9 items-center gap-2 rounded-full bg-teal-50 px-3 text-sm font-bold text-teal-800" onClick={() => apply({ ...filters, weekday: undefined, offset: 0 })} type="button">{WEEKDAY_LABEL[filters.weekday]}<XMarkIcon aria-hidden="true" className="size-4" /></button> : null}{selectedFacility ? <button className="inline-flex min-h-9 items-center gap-2 rounded-full bg-teal-50 px-3 text-sm font-bold text-teal-800" onClick={() => apply({ ...filters, facility_id: undefined, offset: 0 })} type="button">{selectedFacility.name}<XMarkIcon aria-hidden="true" className="size-4" /></button> : null}{locationLabel ? <button className="inline-flex min-h-9 items-center gap-2 rounded-full bg-teal-50 px-3 text-sm font-bold text-teal-800" onClick={() => { locationRef.current = null; setLocationLabel(null); apply({ ...filters, sort: "BEST_MATCH", district_code: undefined, upazila_code: undefined, offset: 0 }); }} type="button"><MapPinIcon aria-hidden="true" className="size-4" />{locationLabel}<XMarkIcon aria-hidden="true" className="size-4" /></button> : null}{(selectedSpecialty || filters.weekday || selectedFacility || locationLabel || filters.query) ? <button className="min-h-9 px-2 text-sm font-bold text-teal-700 underline underline-offset-4" onClick={clearAll} type="button">Clear all</button> : null}<p className="ml-auto text-sm font-semibold text-slate-600">{results ? `${results.total} verified doctor${results.total === 1 ? "" : "s"} found` : ""}</p></div>

    <section aria-label="Doctor search results" className="mt-2 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"><div className="hidden grid-cols-[1.15fr_0.9fr_0.9fr_1.1fr_auto] gap-4 bg-slate-50 px-5 py-3 text-[0.68rem] font-bold uppercase tracking-wide text-slate-500 lg:grid"><span>Doctor</span><span>Specialty</span><span>Facility</span><span>Next practice</span><span className="text-right">Actions</span></div>{loading ? <div className="p-6"><LoadingState description="Finding verified doctors that match your preferences." label="Searching doctors" /></div> : null}{error && !loading ? <div className="p-6"><ErrorState message={error} onAction={() => void runSearch(filters)} title="Doctor search unavailable" /></div> : null}{!loading && !error && results?.items.length === 0 ? <div className="p-6"><EmptyState message={filters.sort === "NEAREST" ? "No confirmed facility was found near this location. Try another area or choose Best match." : "Try another specialty, day, facility, or a broader search."} title="No matching doctors" /></div> : null}{!loading && !error ? results?.items.map((doctor) => <DoctorResult doctor={doctor} key={doctor.id} />) : null}</section>
    {locationOpen ? <LocationDialog areas={areas} locating={locating} onClose={() => setLocationOpen(false)} onGps={chooseGps} onManual={chooseManual} /> : null}
  </main>;
}

function CitizenGuard({ children }: { children: React.ReactNode }) {
  const auth = usePortalAuth("CITIZEN");
  const [hydrationFailed, setHydrationFailed] = useState(false);
  const status = auth.status;
  const refresh = auth.refreshSession;
  useEffect(() => {
    if (status === "authenticated") return;
    let active = true;
    void refresh().catch(() => { if (active) setHydrationFailed(true); });
    return () => { active = false; };
  }, [refresh, status]);
  if (status === "unauthenticated" && !hydrationFailed) return <main className="flex flex-1 items-center px-5 py-12" id="main-content"><LoadingState description="Checking for an active Citizen Portal session." label="Checking Citizen session" /></main>;
  if (status === "unauthenticated") return <main className="flex flex-1 items-center px-5 py-12" id="main-content"><EmptyState action={<Link className="inline-flex min-h-11 items-center justify-center rounded-xl bg-teal-700 px-5 text-sm font-bold text-white" href="/citizen/login?returnTo=%2Fcitizen%2Fdoctors%2Fsearch">Sign in to Citizen Portal</Link>} message="Sign in to search for verified doctors." title="Citizen sign in required" /></main>;
  if (!auth.isRequiredPortal) return <main className="flex flex-1 items-center px-5 py-12" id="main-content"><EmptyState message="This session belongs to another HealthLink portal." title="Citizen Portal access required" /></main>;
  return <>{children}</>;
}

export function DoctorSearch({ searchAction = searchDoctors }: { searchAction?: (filters: DoctorSearchFilters) => Promise<DoctorSearchResponse> }) {
  return <CitizenGuard><SearchContent searchAction={searchAction} /></CitizenGuard>;
}
