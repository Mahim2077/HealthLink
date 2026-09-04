"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { EmptyState, ErrorState, LoadingState } from "@/components/ui/async-state";
import {
  createPrescription,
  downloadPrescriptionPdf,
  readPrescription,
  updatePrescription,
} from "@/lib/prescriptions/api";
import type {
  PrescriptionItemPayload,
  PrescriptionPayload,
  PrescriptionView,
} from "@/lib/prescriptions/types";

export type PrescriptionDeps = {
  create: (visitId: string, payload: PrescriptionPayload) => Promise<PrescriptionView>;
  read: (prescriptionId: string) => Promise<PrescriptionView>;
  update: (
    prescriptionId: string,
    payload: PrescriptionPayload,
  ) => Promise<PrescriptionView>;
  downloadPdf: (prescriptionId: string) => Promise<Blob>;
};

const defaultDeps: PrescriptionDeps = {
  create: createPrescription,
  read: readPrescription,
  update: updatePrescription,
  downloadPdf: downloadPrescriptionPdf,
};

type LoadState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; prescription: PrescriptionView | null };

type MedicineDraft = PrescriptionItemPayload & { clientId: string };

let medicineSequence = 0;

function blankMedicine(): MedicineDraft {
  medicineSequence += 1;
  return {
    clientId: `medicine-${medicineSequence}`,
    medicine_name: "",
    dosage: "",
    frequency: "",
    duration: "",
    instructions: null,
  };
}

function draftsFromPrescription(
  prescription: PrescriptionView | null,
): MedicineDraft[] {
  if (!prescription) return [blankMedicine()];
  return prescription.items.map((item) => ({
    clientId: item.id,
    medicine_name: item.medicine_name,
    dosage: item.dosage,
    frequency: item.frequency,
    duration: item.duration,
    instructions: item.instructions,
  }));
}

function normalizeOptional(value: string): string | null {
  return value.trim() || null;
}

function formatTimestamp(value: string | null): string {
  if (!value) return "Not generated";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

export function PrescriptionPanel({
  visitId,
  prescriptionId,
  editable,
  deps = defaultDeps,
}: {
  visitId?: string;
  prescriptionId?: string | null;
  editable: boolean;
  deps?: PrescriptionDeps;
}) {
  const [loadState, setLoadState] = useState<LoadState>(() =>
    prescriptionId
      ? { kind: "loading" }
      : { kind: "ready", prescription: null },
  );
  const [version, setVersion] = useState(0);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [loadingPdf, setLoadingPdf] = useState(false);

  useEffect(() => {
    if (!prescriptionId) return;
    let active = true;
    void deps.read(prescriptionId).then(
      (prescription) => {
        if (active) setLoadState({ kind: "ready", prescription });
      },
      (reason: unknown) => {
        if (active) {
          setLoadState({
            kind: "error",
            message:
              reason instanceof Error
                ? reason.message
                : "Unable to load prescription",
          });
        }
      },
    );
    return () => {
      active = false;
    };
  }, [deps, prescriptionId, version]);

  useEffect(() => {
    return () => {
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    };
  }, [pdfUrl]);

  const openPdf = useCallback(
    async (prescription: PrescriptionView) => {
      setLoadingPdf(true);
      setPdfError(null);
      try {
        const blob = await deps.downloadPdf(prescription.id);
        setPdfUrl(URL.createObjectURL(blob));
      } catch (reason) {
        setPdfError(
          reason instanceof Error
            ? reason.message
            : "Unable to download prescription PDF",
        );
      } finally {
        setLoadingPdf(false);
      }
    },
    [deps],
  );

  if (loadState.kind === "loading") {
    return (
      <LoadingState
        description="Loading the structured prescription and document status."
        label="Loading prescription"
      />
    );
  }
  if (loadState.kind === "error") {
    return (
      <ErrorState
        message={loadState.message}
        onAction={() => {
          setLoadState({ kind: "loading" });
          setVersion((value) => value + 1);
        }}
        title="Prescription unavailable"
      />
    );
  }

  const prescription = loadState.prescription;
  if (!prescription && !visitId) {
    return (
      <EmptyState
        message="The requested prescription could not be identified."
        title="Prescription unavailable"
      />
    );
  }

  const save = async (payload: PrescriptionPayload) => {
    const saved = prescription
      ? await deps.update(prescription.id, payload)
      : await deps.create(visitId as string, payload);
    setLoadState({ kind: "ready", prescription: saved });
  };

  return (
    <section className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
      <header className="flex flex-col gap-3 border-b border-slate-200 pb-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.15em] text-teal-700">
            Electronic prescription
          </p>
          <h2 className="mt-2 text-2xl font-bold text-slate-950">
            {prescription ? "Structured prescription" : "Create prescription"}
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Medicine rows remain the source of truth. The PDF is regenerated from
            this structured record after every successful save.
          </p>
        </div>
        {prescription && editable ? (
          <Link
            className="text-sm font-bold text-sky-700 hover:text-sky-900"
            href={`/professional/prescriptions/${prescription.id}`}
          >
            Open prescription page →
          </Link>
        ) : null}
      </header>

      {editable ? (
        <PrescriptionForm
          key={prescription?.updated_at ?? `new-${visitId}`}
          initialPrescription={prescription}
          onSave={save}
        />
      ) : prescription ? (
        <PrescriptionReadOnly prescription={prescription} />
      ) : null}

      {prescription ? (
        <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-bold text-slate-900">Prescription PDF</p>
              <p className="mt-1 text-xs text-slate-600">
                {prescription.pdf_available
                  ? `Generated ${formatTimestamp(prescription.pdf_updated_at)}`
                  : "The structured record is safe, but its PDF needs regeneration."}
              </p>
            </div>
            <button
              className="inline-flex min-h-11 items-center justify-center rounded-xl bg-teal-700 px-5 text-sm font-bold text-white disabled:opacity-60"
              disabled={!prescription.pdf_available || loadingPdf}
              onClick={() => void openPdf(prescription)}
              type="button"
            >
              {loadingPdf ? "Loading PDF…" : "View / download PDF"}
            </button>
          </div>
          {!prescription.pdf_available && editable ? (
            <p className="mt-3 text-sm text-amber-800">
              Save the prescription again to retry PDF generation.
            </p>
          ) : null}
          {pdfError ? (
            <p className="mt-3 text-sm text-rose-700" role="alert">
              {pdfError}
            </p>
          ) : null}
          {pdfUrl ? (
            <div className="mt-5">
              <iframe
                className="h-[34rem] w-full rounded-xl border border-slate-300 bg-white"
                src={pdfUrl}
                title="Prescription PDF preview"
              />
              <a
                className="mt-3 inline-flex min-h-11 items-center text-sm font-bold text-teal-700"
                download={prescription.pdf_file_name ?? "prescription.pdf"}
                href={pdfUrl}
              >
                Download PDF
              </a>
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

function PrescriptionForm({
  initialPrescription,
  onSave,
}: {
  initialPrescription: PrescriptionView | null;
  onSave: (payload: PrescriptionPayload) => Promise<void>;
}) {
  const [medicines, setMedicines] = useState<MedicineDraft[]>(() =>
    draftsFromPrescription(initialPrescription),
  );
  const [diagnosticInformation, setDiagnosticInformation] = useState(
    initialPrescription?.diagnostic_information ?? "",
  );
  const [medicalAdvice, setMedicalAdvice] = useState(
    initialPrescription?.medical_advice ?? "",
  );
  const [notes, setNotes] = useState(initialPrescription?.notes ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateMedicine = (
    clientId: string,
    field: keyof PrescriptionItemPayload,
    value: string,
  ) => {
    setMedicines((current) =>
      current.map((medicine) =>
        medicine.clientId === clientId
          ? { ...medicine, [field]: value }
          : medicine,
      ),
    );
  };

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    const items = medicines.map((medicine) => ({
      medicine_name: medicine.medicine_name.trim(),
      dosage: medicine.dosage.trim(),
      frequency: medicine.frequency.trim(),
      duration: medicine.duration.trim(),
      instructions: normalizeOptional(medicine.instructions ?? ""),
    }));
    if (
      items.some(
        (item) =>
          !item.medicine_name ||
          !item.dosage ||
          !item.frequency ||
          !item.duration,
      )
    ) {
      setError("Complete every required medicine field before saving.");
      return;
    }

    setSaving(true);
    try {
      await onSave({
        items,
        diagnostic_information: normalizeOptional(diagnosticInformation),
        medical_advice: normalizeOptional(medicalAdvice),
        notes: normalizeOptional(notes),
      });
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Unable to save prescription",
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="mt-6" onSubmit={submit}>
      <fieldset disabled={saving}>
        <legend className="text-sm font-bold text-slate-900">Medicines</legend>
        <div className="mt-3 space-y-4">
          {medicines.map((medicine, index) => (
            <div
              className="rounded-2xl border border-slate-200 bg-slate-50 p-4"
              data-testid="medicine-row"
              key={medicine.clientId}
            >
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-bold text-slate-900">
                  Medicine {index + 1}
                </p>
                <button
                  className="min-h-10 rounded-lg px-3 text-sm font-bold text-rose-700 disabled:text-slate-400"
                  disabled={medicines.length === 1}
                  onClick={() =>
                    setMedicines((current) =>
                      current.filter((row) => row.clientId !== medicine.clientId),
                    )
                  }
                  type="button"
                >
                  Remove Medicine
                </button>
              </div>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                {(
                  [
                    ["medicine_name", "Medicine name", 200],
                    ["dosage", "Dosage", 100],
                    ["frequency", "Frequency", 100],
                    ["duration", "Duration", 100],
                  ] as const
                ).map(([field, label, maxLength]) => (
                  <label className="block text-sm" key={field}>
                    <span className="font-semibold text-slate-700">{label}</span>
                    <input
                      className="mt-1 block min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm"
                      maxLength={maxLength}
                      onChange={(event) =>
                        updateMedicine(medicine.clientId, field, event.target.value)
                      }
                      required
                      value={medicine[field] ?? ""}
                    />
                  </label>
                ))}
                <label className="block text-sm sm:col-span-2">
                  <span className="font-semibold text-slate-700">Instructions</span>
                  <textarea
                    className="mt-1 block w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm"
                    maxLength={4000}
                    onChange={(event) =>
                      updateMedicine(
                        medicine.clientId,
                        "instructions",
                        event.target.value,
                      )
                    }
                    rows={2}
                    value={medicine.instructions ?? ""}
                  />
                </label>
              </div>
            </div>
          ))}
        </div>
        <button
          className="mt-4 min-h-11 rounded-xl border border-sky-200 bg-sky-50 px-4 text-sm font-bold text-sky-800"
          onClick={() => setMedicines((current) => [...current, blankMedicine()])}
          type="button"
        >
          + Add Medicine
        </button>

        <div className="mt-6 grid gap-4">
          {(
            [
              [
                "Diagnostic information",
                diagnosticInformation,
                setDiagnosticInformation,
              ],
              ["Medical advice", medicalAdvice, setMedicalAdvice],
              ["Notes", notes, setNotes],
            ] as const
          ).map(([label, value, setter]) => (
            <label className="block text-sm" key={label}>
              <span className="font-semibold text-slate-700">{label}</span>
              <textarea
                className="mt-1 block w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
                maxLength={8000}
                onChange={(event) => setter(event.target.value)}
                rows={3}
                value={value}
              />
            </label>
          ))}
        </div>
      </fieldset>

      {error ? (
        <p className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800" role="alert">
          {error}
        </p>
      ) : null}
      <button
        className="mt-5 inline-flex min-h-11 items-center rounded-xl bg-teal-700 px-5 text-sm font-bold text-white disabled:opacity-60"
        disabled={saving}
        type="submit"
      >
        {saving
          ? "Saving prescription…"
          : initialPrescription
            ? "Update prescription"
            : "Save prescription"}
      </button>
    </form>
  );
}

function PrescriptionReadOnly({
  prescription,
}: {
  prescription: PrescriptionView;
}) {
  return (
    <div className="mt-6 space-y-6">
      <div className="grid gap-4">
        {prescription.items.map((item, index) => (
          <article className="rounded-2xl border border-slate-200 p-5" key={item.id}>
            <p className="text-xs font-bold uppercase tracking-[0.15em] text-teal-700">
              Medicine {index + 1}
            </p>
            <h3 className="mt-2 text-lg font-bold text-slate-950">
              {item.medicine_name}
            </h3>
            <dl className="mt-3 grid gap-2 text-sm text-slate-700 sm:grid-cols-3">
              <div><dt className="font-semibold">Dosage</dt><dd>{item.dosage}</dd></div>
              <div><dt className="font-semibold">Frequency</dt><dd>{item.frequency}</dd></div>
              <div><dt className="font-semibold">Duration</dt><dd>{item.duration}</dd></div>
            </dl>
            {item.instructions ? (
              <p className="mt-3 text-sm text-slate-600">{item.instructions}</p>
            ) : null}
          </article>
        ))}
      </div>
      <dl className="grid gap-4 sm:grid-cols-3">
        <TextBlock label="Diagnostic information" value={prescription.diagnostic_information} />
        <TextBlock label="Medical advice" value={prescription.medical_advice} />
        <TextBlock label="Notes" value={prescription.notes} />
      </dl>
    </div>
  );
}

function TextBlock({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="rounded-2xl bg-slate-50 p-4">
      <dt className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
        {label}
      </dt>
      <dd className="mt-2 whitespace-pre-wrap text-sm text-slate-800">
        {value ?? "Not provided"}
      </dd>
    </div>
  );
}
