import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { PrescriptionView } from "@/lib/prescriptions/types";

import { PrescriptionPanel, type PrescriptionDeps } from "./prescription-panel";

function prescription(
  overrides: Partial<PrescriptionView> = {},
): PrescriptionView {
  return {
    id: "rx-1",
    visit_id: "visit-1",
    citizen_id: "citizen-1",
    author_doctor_role_registration_id: "doctor-role-1",
    chief_complaint: "Fever and sore throat",
    clinical_notes: "Temperature 38°C",
    diagnosis: "Viral fever",
    follow_up_instructions: "Review after three days if needed",
    items: [
      {
        id: "item-1",
        medicine_name: "Paracetamol",
        dosage: "500 mg",
        frequency: "1+0+1",
        duration: "5 days",
        instructions: "After meals",
      },
    ],
    diagnostic_information: "Viral fever",
    medical_advice: "Rest and hydrate",
    notes: null,
    can_edit: true,
    created_at: "2026-08-21T12:00:00Z",
    updated_at: "2026-08-21T12:00:00Z",
    ...overrides,
  };
}

function dependencies(): PrescriptionDeps {
  return {
    create: vi.fn(),
    read: vi.fn(),
    update: vi.fn(),
    downloadPdf: vi.fn(),
  };
}

describe("PrescriptionPanel", () => {
  beforeEach(() => {
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:prescription-preview"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
  });

  it("adds and removes medicine rows and saves all structured fields", async () => {
    const deps = dependencies();
    vi.mocked(deps.create).mockResolvedValue(prescription());
    render(
      <PrescriptionPanel deps={deps} editable visitId="visit-1" />,
    );

    fireEvent.click(screen.getByRole("button", { name: "+ Add Medicine" }));
    expect(screen.getAllByTestId("medicine-row")).toHaveLength(2);
    fireEvent.click(
      screen.getAllByRole("button", { name: "Remove Medicine" })[1],
    );
    expect(screen.getAllByTestId("medicine-row")).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: "+ Add Medicine" }));

    const rows = screen.getAllByTestId("medicine-row");
    const medicines = [
      ["Paracetamol", "500 mg", "1+0+1", "5 days", "After meals"],
      ["Cetirizine", "10 mg", "0+0+1", "3 days", "At bedtime"],
    ];
    rows.forEach((row, index) => {
      const fields = within(row);
      fireEvent.change(fields.getByLabelText("Medicine name"), {
        target: { value: medicines[index][0] },
      });
      fireEvent.change(fields.getByLabelText("Dosage"), {
        target: { value: medicines[index][1] },
      });
      fireEvent.change(fields.getByLabelText("Frequency"), {
        target: { value: medicines[index][2] },
      });
      fireEvent.change(fields.getByLabelText("Duration"), {
        target: { value: medicines[index][3] },
      });
      fireEvent.change(fields.getByLabelText("Instructions"), {
        target: { value: medicines[index][4] },
      });
    });
    fireEvent.change(screen.getByLabelText("Diagnostic information"), {
      target: { value: " Seasonal allergy " },
    });
    fireEvent.change(screen.getByLabelText("Clinical notes"), {
      target: { value: " Mild wheeze " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save consultation & prescription" }));

    await waitFor(() => expect(deps.create).toHaveBeenCalledOnce());
    expect(deps.create).toHaveBeenCalledWith("visit-1", {
      items: [
        {
          medicine_name: "Paracetamol",
          dosage: "500 mg",
          frequency: "1+0+1",
          duration: "5 days",
          instructions: "After meals",
        },
        {
          medicine_name: "Cetirizine",
          dosage: "10 mg",
          frequency: "0+0+1",
          duration: "3 days",
          instructions: "At bedtime",
        },
      ],
      chief_complaint: null,
      clinical_notes: "Mild wheeze",
      diagnosis: null,
      follow_up_instructions: null,
      diagnostic_information: "Seasonal allergy",
      medical_advice: null,
      notes: null,
    });
  });

  it("shows a citizen the structured record and protected PDF", async () => {
    const deps = dependencies();
    const record = prescription();
    vi.mocked(deps.read).mockResolvedValue(record);
    vi.mocked(deps.downloadPdf).mockResolvedValue(
      new Blob(["%PDF"], { type: "application/pdf" }),
    );
    render(
      <PrescriptionPanel
        deps={deps}
        editable={false}
        prescriptionId="rx-1"
      />,
    );

    expect(await screen.findByText("Paracetamol")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Update prescription" }),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Generate PDF" }));

    await waitFor(() => expect(deps.downloadPdf).toHaveBeenCalledWith("rx-1"));
    expect(await screen.findByTitle("Prescription PDF preview")).toHaveAttribute(
      "src",
      "blob:prescription-preview",
    );
    expect(screen.getByRole("link", { name: "Download PDF" })).toHaveAttribute(
      "download",
      "prescription-rx-1.pdf",
    );
  });

  it("shows previous prescriptions read-only to an authorized non-author doctor", async () => {
    const deps = dependencies();
    vi.mocked(deps.read).mockResolvedValue(prescription({ can_edit: false }));
    render(
      <PrescriptionPanel deps={deps} editable prescriptionId="rx-1" />,
    );

    expect(await screen.findByText("Fever and sore throat")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /update consultation/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generate PDF" })).toBeEnabled();
  });

  it("generates a previous prescription PDF as soon as the doctor opens it", async () => {
    const deps = dependencies();
    vi.mocked(deps.read).mockResolvedValue(prescription({ can_edit: false }));
    vi.mocked(deps.downloadPdf).mockResolvedValue(
      new Blob(["%PDF"], { type: "application/pdf" }),
    );
    render(
      <PrescriptionPanel
        autoGeneratePdf
        deps={deps}
        editable
        prescriptionId="rx-1"
      />,
    );

    await waitFor(() => expect(deps.downloadPdf).toHaveBeenCalledWith("rx-1"));
    expect(await screen.findByTitle("Prescription PDF preview")).toHaveAttribute(
      "src",
      "blob:prescription-preview",
    );
  });

  it("clears and revokes an opened PDF after a prescription update", async () => {
    const deps = dependencies();
    vi.mocked(deps.read).mockResolvedValue(prescription());
    vi.mocked(deps.downloadPdf).mockResolvedValue(new Blob(["%PDF"], { type: "application/pdf" }));
    vi.mocked(deps.update).mockResolvedValue(prescription({ medical_advice: "Updated advice", updated_at: "2026-08-21T13:00:00Z" }));
    render(<PrescriptionPanel deps={deps} editable prescriptionId="rx-1" />);
    fireEvent.click(await screen.findByRole("button", { name: "Generate PDF" }));
    await screen.findByTitle("Prescription PDF preview");
    fireEvent.change(screen.getByLabelText("Medical advice"), { target: { value: "Updated advice" } });
    fireEvent.click(screen.getByRole("button", { name: "Update consultation & prescription" }));
    await waitFor(() => expect(screen.queryByTitle("Prescription PDF preview")).not.toBeInTheDocument());
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:prescription-preview");
  });
});
