import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ConsultationWorkspace, type VisitsDeps } from "./consultation-workspace";
import type {
  DoctorCurrentPatientView,
  VisitDraftView,
} from "@/lib/visits/types";

const baseQueueId = "queue-1";
const baseVisitId = "visit-1";

const baseCurrent = (
  overrides: Partial<DoctorCurrentPatientView>,
): DoctorCurrentPatientView => ({
  appointment_id: "appt-1",
  citizen_id: "citizen-1",
  facility_id: "facility-1",
  facility_name: "City Hospital",
  patient: {
    age_years: 35,
    blood_group: "O+",
    citizen_id: "citizen-1",
    date_of_birth: "1990-05-01",
    full_name: "Sadia Khan",
    gender: "FEMALE",
  },
  queue_id: baseQueueId,
  serial_number: 1,
  visit: null,
  ...overrides,
});

const baseVisit = (overrides: Partial<VisitDraftView>): VisitDraftView => ({
  access_source: "queue",
  appointment_id: "appt-1",
  prescription_id: null,
  chief_complaint: null,
  citizen_id: "citizen-1",
  clinical_notes: null,
  diagnosis: null,
  doctor_role_registration_id: "reg-1",
  facility_id: "facility-1",
  finalized_at: null,
  follow_up_instructions: null,
  id: baseVisitId,
  patient: null,
  status: "DRAFT",
  updated_at: "2026-08-10T09:30:00Z",
  visit_date: "2026-08-10T09:30:00Z",
  ...overrides,
});

function buildDeps(
  overrides: Partial<VisitsDeps> = {},
): { deps: VisitsDeps; spies: VisitsDeps } {
  const spies: VisitsDeps = {
    loadCurrentPatient: vi.fn().mockResolvedValue(null),
    readVisit: vi.fn().mockResolvedValue({} as never),
    startVisitForCurrent: vi.fn().mockResolvedValue({} as never),
    updateVisit: vi.fn().mockResolvedValue({} as never),
  };
  return { deps: { ...spies, ...overrides }, spies };
}

describe("ConsultationWorkspace", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("renders the empty state when there is no current patient", async () => {
    const { deps } = buildDeps();
    render(<ConsultationWorkspace visitsDeps={deps} />);
    expect(
      await screen.findByText(/no active patient/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /open consultation/i }),
    ).not.toBeInTheDocument();
  });

  it("opens a draft visit and saves clinical notes for the current patient", async () => {
    const startVisit = vi.fn().mockResolvedValue(
      baseVisit({
        chief_complaint: "fever",
        clinical_notes: "rest",
        diagnosis: "viral",
      }),
    );
    const updateVisit = vi.fn().mockImplementation(
      async (_id: string, payload: { clinical_notes?: string }) => ({
        ...baseVisit({}),
        clinical_notes: payload.clinical_notes ?? null,
      }),
    );

    const { deps } = buildDeps({
      loadCurrentPatient: vi.fn().mockResolvedValue(baseCurrent({ visit: null })),
      startVisitForCurrent: startVisit,
      updateVisit,
    });

    render(<ConsultationWorkspace visitsDeps={deps} />);

    expect(
      await screen.findByRole("heading", { name: /serial #1/i }),
    ).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: /open consultation/i }),
    );

    await waitFor(() => {
      expect(startVisit).toHaveBeenCalledWith(baseQueueId);
    });

    const notes = await screen.findByLabelText(/clinical notes/i);
    fireEvent.change(notes, { target: { value: "Temp 38C" } });
    fireEvent.click(screen.getByRole("button", { name: /save draft/i }));

    await waitFor(() => {
      expect(updateVisit).toHaveBeenCalledWith(
        baseVisitId,
        expect.objectContaining({ clinical_notes: "Temp 38C" }),
      );
    });
  });

  it("disables editing when the visit is finalized", async () => {
    const { deps } = buildDeps({
      loadCurrentPatient: vi
        .fn()
        .mockResolvedValue(
          baseCurrent({ visit: baseVisit({ status: "FINALIZED" }) }),
        ),
    });

    render(<ConsultationWorkspace visitsDeps={deps} />);

    expect(
      await screen.findByText(/further edits are disabled/i),
    ).toBeInTheDocument();
    expect(
      (screen.getByLabelText(/clinical notes/i) as HTMLTextAreaElement).disabled,
    ).toBe(true);
    expect(
      (screen.getByRole("button", { name: /save draft/i }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
  });

  it("shows an error banner when starting a visit fails", async () => {
    const { deps } = buildDeps({
      loadCurrentPatient: vi.fn().mockResolvedValue(baseCurrent({ visit: null })),
      startVisitForCurrent: vi
        .fn()
        .mockRejectedValue(new Error("Conflict: queue raced")),
    });

    render(<ConsultationWorkspace visitsDeps={deps} />);

    await screen.findByRole("heading", { name: /serial #1/i });
    fireEvent.click(
      screen.getByRole("button", { name: /open consultation/i }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /conflict: queue raced/i,
    );
  });
});
