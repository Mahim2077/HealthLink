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
    pdf_available: true,
    pdf_file_name: "prescription-rx-1.pdf",
    pdf_updated_at: "2026-08-21T12:00:00Z",
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
    fireEvent.click(screen.getByRole("button", { name: "Save prescription" }));

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
    fireEvent.click(
      screen.getByRole("button", { name: "View / download PDF" }),
    );

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

  it("lets the author retry PDF generation by updating the saved record", async () => {
    const deps = dependencies();
    const unavailable = prescription({
      pdf_available: false,
      pdf_file_name: null,
      pdf_updated_at: null,
    });
    vi.mocked(deps.read).mockResolvedValue(unavailable);
    vi.mocked(deps.update).mockResolvedValue(prescription());
    render(
      <PrescriptionPanel deps={deps} editable prescriptionId="rx-1" />,
    );

    expect(
      await screen.findByText("Save the prescription again to retry PDF generation."),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Update prescription" }));

    await waitFor(() => expect(deps.update).toHaveBeenCalledOnce());
    expect(deps.update).toHaveBeenCalledWith(
      "rx-1",
      expect.objectContaining({
        items: [
          expect.objectContaining({ medicine_name: "Paracetamol" }),
        ],
      }),
    );
  });
});
