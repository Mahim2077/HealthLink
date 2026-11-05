import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { MedicalHistoryPage } from "@/lib/medical-records/types";
import { MedicalHistoryTimeline } from "./medical-history-timeline";

const page = (overrides: Partial<MedicalHistoryPage> = {}): MedicalHistoryPage => ({
  has_next: false,
  items: [
    {
      appointment_id: "appointment-1",
      facility: "City Hospital",
      id: "prescription:prescription-1",
      occurred_at: "2026-08-10T10:00:00Z",
      professional: "Dr Nusrat Karim",
      resource_id: "prescription-1",
      resource_type: "PRESCRIPTION",
      serial_number: 4,
      status: "AVAILABLE",
      subtitle: "2 medicines",
      summary: "Seasonal allergy",
      title: "Prescription",
    },
  ],
  page: 1,
  page_size: 10,
  total: 1,
  ...overrides,
});

describe("MedicalHistoryTimeline", () => {
  it("renders citizen history and links an owned prescription", async () => {
    const loadAction = vi.fn().mockResolvedValue(page());
    render(<MedicalHistoryTimeline loadAction={loadAction} portal="citizen" />);

    expect(await screen.findByText("Seasonal allergy")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /open prescription/i })).toHaveAttribute(
      "href",
      "/citizen/prescriptions/prescription-1?returnTo=%2Fcitizen%2Fmedical-history",
    );
    expect(loadAction).toHaveBeenCalledWith({ page: 1, page_size: 10 });
  });

  it("applies filters and advances through stable pages", async () => {
    const loadAction = vi
      .fn()
      .mockResolvedValueOnce(page())
      .mockResolvedValueOnce(page({ has_next: true, total: 12 }))
      .mockResolvedValueOnce(page({ page: 2 }));
    render(<MedicalHistoryTimeline loadAction={loadAction} portal="citizen" />);
    await screen.findByText("Seasonal allergy");

    fireEvent.change(screen.getByLabelText("Record type"), {
      target: { value: "PRESCRIPTION" },
    });
    fireEvent.change(screen.getByLabelText("From"), {
      target: { value: "2026-08-01" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply" }));

    await waitFor(() =>
      expect(loadAction).toHaveBeenNthCalledWith(2, {
        resource_type: "PRESCRIPTION",
        date_from: "2026-08-01",
        page: 1,
        page_size: 10,
      }),
    );
    fireEvent.click(await screen.findByRole("button", { name: "Next" }));
    await waitFor(() =>
      expect(loadAction).toHaveBeenNthCalledWith(3, {
        resource_type: "PRESCRIPTION",
        date_from: "2026-08-01",
        page: 2,
        page_size: 10,
      }),
    );
    const prescriptionLink = await screen.findByRole("link", { name: /open prescription/i });
    expect(new URL(prescriptionLink.getAttribute("href")!, "http://localhost").searchParams.get("returnTo")).toBe(
      "/citizen/medical-history?resource_type=PRESCRIPTION&date_from=2026-08-01&page=2",
    );
  });

  it("restores the applied history filters and page supplied by a prescription return link", async () => {
    const initialQuery = { resource_type: "PRESCRIPTION" as const, date_from: "2026-08-01", date_to: "2026-08-31", page: 2, page_size: 10 };
    const loadAction = vi.fn().mockResolvedValue(page({ page: 2 }));
    render(<MedicalHistoryTimeline initialQuery={initialQuery} loadAction={loadAction} portal="citizen" />);
    await screen.findByText("Seasonal allergy");
    expect(screen.getByLabelText("Record type")).toHaveValue("PRESCRIPTION");
    expect(screen.getByLabelText("From")).toHaveValue("2026-08-01");
    expect(screen.getByLabelText("To")).toHaveValue("2026-08-31");
    expect(loadAction).toHaveBeenCalledWith(initialQuery);
    expect(screen.getByText("Page 2")).toBeInTheDocument();
  });

  it("lets a doctor open an authorized previous prescription", async () => {
    render(
      <MedicalHistoryTimeline
        loadAction={vi.fn().mockResolvedValue(page())}
        portal="professional"
      />,
    );
    await screen.findByText("Seasonal allergy");
    expect(screen.getByRole("link", { name: /open previous prescription/i })).toHaveAttribute(
      "href",
      "/professional/prescriptions/prescription-1",
    );
  });
});
