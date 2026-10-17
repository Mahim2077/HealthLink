import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AdminCareOverview, CitizenCareOverview, ProfessionalCareOverview } from "./care-overview";
import type { CitizenOverview, ProfessionalOverview } from "@/lib/overview";

const citizen: CitizenOverview = { today: "2026-10-02", upcoming_appointment: null, recent_prescription: null, latest_report: null, active_reminders: 0, unread_notifications: 0, emergency_profile_updated_at: null };
const professional: ProfessionalOverview = { today: "2026-10-02", role_code: "LAB_TECHNICIAN", chambers: [], chambers_has_more: false, requested_tests: 3, in_progress_tests: 2, draft_reports: 1, finalized_reports: 4, recent_prescription: null };

describe("read-only care dashboards", () => {
  it("preserves merged diagnostics and explainer AI with honest reminder status", async () => {
    render(<CitizenCareOverview load={vi.fn().mockResolvedValue(citizen)} />);
    expect(await screen.findByText("Nothing booked")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Latest diagnostic result/ })).toHaveAttribute("href", "/citizen/diagnostic-tests");
    expect(screen.getByRole("link", { name: /AI assistant/ })).toHaveAttribute("href", "/citizen/ai-assistant");
    expect(screen.getByText(/Automatic reminder delivery is not enabled/)).toBeInTheDocument();
  });
  it("links source prescriptions and reports using the diagnostic-test ID", async () => {
    render(<CitizenCareOverview load={vi.fn().mockResolvedValue({ ...citizen, recent_prescription: { id: "rx-1", created_at: "2026-10-01" }, latest_report: { diagnostic_test_id: "test-1", test_name: "Synthetic CBC", report_date: "2026-10-01" } })} />);
    expect(await screen.findByText("Synthetic CBC")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Recent prescription/ })).toHaveAttribute("href", "/citizen/prescriptions/rx-1");
    expect(screen.getByRole("link", { name: /Latest diagnostic result/ })).toHaveAttribute("href", "/citizen/diagnostic-tests/test-1");
  });
  it("shows lab workload without doctor chamber controls", async () => {
    render(<ProfessionalCareOverview role="LAB_TECHNICIAN" load={vi.fn().mockResolvedValue(professional)} />);
    expect(await screen.findByText("Draft reports")).toBeInTheDocument();
    expect(screen.getByText("Finalized reports")).toBeInTheDocument();
    expect(screen.queryByText("Open chamber queue")).not.toBeInTheDocument();
  });
  it("shows the current serial without patient identity", async () => {
    render(<ProfessionalCareOverview role="DOCTOR" load={vi.fn().mockResolvedValue({ ...professional, role_code: "DOCTOR", chambers: [{ facility_name: "Test Hospital", status: "ACTIVE", waiting_count: 2, current_serial: 4 }] })} />);
    expect(await screen.findByText(/Current serial 4/)).toBeInTheDocument();
    expect(screen.queryByText("Draft reports")).not.toBeInTheDocument();
  });
  it("refuses a response for the wrong selected role", async () => {
    render(<ProfessionalCareOverview role="DOCTOR" load={vi.fn().mockResolvedValue(professional)} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("active role changed");
  });
  it("retries a failed overview without fake zero counts", async () => {
    const load = vi.fn().mockRejectedValueOnce(new Error("Synthetic failure")).mockResolvedValueOnce({ pending_professional_registrations: 7, active_facilities: 5, facilities_needing_location: 2 });
    render(<AdminCareOverview load={load} />);
    expect(await screen.findByText("Overview unavailable")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /try again|retry/i }));
    expect(await screen.findByText("7")).toBeInTheDocument();
  });
  it("drops a late response after switching roles", async () => {
    let resolve!: (value: ProfessionalOverview) => void;
    const load = vi.fn().mockImplementationOnce(() => new Promise<ProfessionalOverview>(done => { resolve = done; })).mockResolvedValueOnce(professional);
    const view = render(<ProfessionalCareOverview role="DOCTOR" load={load} />);
    view.rerender(<ProfessionalCareOverview role="LAB_TECHNICIAN" load={load} />);
    expect(await screen.findByText("Draft reports")).toBeInTheDocument();
    resolve({ ...professional, role_code: "DOCTOR", chambers: [{ facility_name: "Old facility", status: "ACTIVE", waiting_count: 1, current_serial: 1 }] });
    await waitFor(() => expect(screen.queryByText("Old facility")).not.toBeInTheDocument());
  });
});
