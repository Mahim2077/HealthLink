import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LabPortalGate, LabReportEditor } from "./lab-report-page";
import { LabTrendTables } from "./citizen-lab-reports";
import type { LabReport } from "@/lib/diagnostics/report-api";

const mocks = vi.hoisted(() => ({ save: vi.fn(), finalize: vi.fn(), auth: vi.fn() }));
vi.mock("@/lib/diagnostics/report-api", () => ({ saveLabReport: mocks.save, finalizeLabReport: mocks.finalize }));
vi.mock("@/components/auth/auth-provider", () => ({ usePortalAuth: mocks.auth }));
const report: LabReport = { id: "report", diagnostic_test_id: "test", citizen_id: "citizen", status: "DRAFT", finalized_at: null, test_name: "CBC", facility_name: "City hospital", report_date: "2026-01-01", summary: "Draft", items: [{ parameter_name: "Haemoglobin", result_value_text: "13.2", result_value_numeric: "13.2", unit: "g/dL", reference_range: null, flag: null }] };

describe("Lab reports", () => {
  beforeEach(() => { vi.clearAllMocks(); });
  it("retains failed edits and blocks finalization until saved", async () => {
    mocks.save.mockRejectedValue(new Error("Save unavailable"));
    render(<LabReportEditor testId="test" initial={report} />);
    fireEvent.change(screen.getByLabelText("Summary"), { target: { value: "Correction" } });
    expect(screen.getByRole("button", { name: "Finalize report" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Save unavailable");
    expect(screen.getByLabelText("Summary")).toHaveValue("Correction");
    expect(mocks.save).toHaveBeenCalledWith("test", expect.objectContaining({ summary: "Correction", items: report.items }));
  });
  it("prevents duplicate saves and edits while saving", async () => {
    let resolve!: (value: LabReport) => void;
    mocks.save.mockReturnValue(new Promise<LabReport>(r => { resolve = r; }));
    render(<LabReportEditor testId="test" initial={report} />);
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    expect(screen.getByLabelText("Result")).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Saving…" }));
    expect(mocks.save).toHaveBeenCalledTimes(1);
    await act(async () => resolve(report));
  });
  it("requires confirmation and makes a finalized report read-only", async () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValueOnce(false).mockReturnValueOnce(true);
    mocks.finalize.mockResolvedValue({ ...report, status: "FINALIZED", finalized_at: "2026-01-01T10:00:00Z" });
    render(<LabReportEditor testId="test" initial={report} />);
    fireEvent.click(screen.getByRole("button", { name: "Finalize report" }));
    expect(mocks.finalize).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Finalize report" }));
    expect(await screen.findByText("Finalized report — read only.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Save draft" })).not.toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Lab report results" })).toBeInTheDocument();
    confirm.mockRestore();
  });
  it("keeps incompatible units in separate accessible tables", () => {
    render(<LabTrendTables points={[
      { report_id: "one", report_date: "2026-01-01", parameter_name: "Haemoglobin", value: "13.2", unit: "g/dL" },
      { report_id: "two", report_date: "2026-01-02", parameter_name: "Haemoglobin", value: "132", unit: "g/L" },
    ]} />);
    expect(screen.getAllByRole("table")).toHaveLength(2);
    expect(within(screen.getByRole("table", { name: "Haemoglobin — g/dL" })).queryByText("132")).toBeNull();
  });
  it("does not mount private content for the wrong portal", () => {
    mocks.auth.mockReturnValue({ status: "authenticated", isRequiredPortal: false, refreshSession: vi.fn() });
    render(<LabPortalGate portal="CITIZEN"><p>Private results</p></LabPortalGate>);
    expect(screen.queryByText("Private results")).toBeNull();
  });
});
