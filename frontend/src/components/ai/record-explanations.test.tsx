import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ prescription: vi.fn(), lab: vi.fn(), history: vi.fn() }));
vi.mock("@/lib/ai/api", () => ({ explainPrescription: mocks.prescription, explainLabReport: mocks.lab, summarizeMedicalHistory: mocks.history }));

import { LabReportExplanation } from "./lab-report-explanation";
import { MedicalHistorySummary } from "./medical-history-summary";
import { PrescriptionExplanation } from "./prescription-explanation";

describe("record AI explanations", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders a prescription explanation as secondary information", async () => {
    mocks.prescription.mockResolvedValue({ plain_language_summary: "This record contains one medicine.", medicine_explanations: [{ medicine_name: "Medicine A", purpose_or_role: "The record does not state why this medicine was prescribed.", general_education: "General explanation of the recorded medicine.", recorded_instructions: "After meals" }], questions_to_ask_clinician: ["When should I follow up?"], disclaimer: "Not medical advice." });
    render(<PrescriptionExplanation prescriptionId="rx-1" />);
    fireEvent.click(screen.getByRole("button", { name: "Explain with AI" }));
    expect(await screen.findByText("This record contains one medicine.")).toBeInTheDocument();
    expect(mocks.prescription).toHaveBeenCalledWith("rx-1");
    expect(screen.getByText("General medicine knowledge")).toBeInTheDocument();
    expect(screen.getByText("General explanation of the recorded medicine.")).toBeInTheDocument();
    expect(screen.getByText("General education, not a confirmed reason for your prescription.")).toBeInTheDocument();
    expect(screen.getByText("The record does not state why this medicine was prescribed.")).toBeInTheDocument();
    expect(screen.getByText(/Doctor's recorded instructions \(unchanged\): After meals/)).toBeInTheDocument();
  });

  it("renders finalized lab parameter context", async () => {
    mocks.lab.mockResolvedValue({ summary: "CBC summary", parameter_explanations: [{ parameter: "Haemoglobin", result: "13.2", unit: "g/dL", reference_range: "12–16", flag: null, explanation: "This value was not flagged." }], flagged_results: [], questions_for_clinician: [], disclaimer: "Not a diagnosis." });
    render(<LabReportExplanation reportId="report-1" />);
    fireEvent.click(screen.getByRole("button", { name: "Explain with AI" }));
    expect(await screen.findByText("This value was not flagged.")).toBeInTheDocument();
    expect(mocks.lab).toHaveBeenCalledWith("report-1");
  });

  it("blocks medical-history summary until consent", async () => {
    mocks.history.mockResolvedValue({ summary: "History summary", record_observations: [], questions_for_clinician: [], disclaimer: "Not a diagnosis.", records_used: {} });
    render(<MedicalHistorySummary />);
    const button = screen.getByRole("button", { name: "Generate AI summary" });
    expect(button).toBeDisabled();
    fireEvent.click(screen.getByText(/I allow HealthLink AI/));
    fireEvent.click(button);
    await waitFor(() => expect(mocks.history).toHaveBeenCalledOnce());
    expect(await screen.findByText("History summary")).toBeInTheDocument();
    expect(screen.getByRole("checkbox")).not.toBeChecked();
    expect(screen.getByRole("button", { name: "Refresh AI summary" })).toBeDisabled();
  });

  it("clears an old summary before refresh and requires new consent after failure", async () => {
    mocks.history.mockResolvedValueOnce({ summary: "Old summary", record_observations: [], questions_for_clinician: [], disclaimer: "Not a diagnosis.", records_used: {} });
    let reject!: (reason: Error) => void;
    mocks.history.mockImplementationOnce(() => new Promise((_, rejectRequest) => { reject = rejectRequest; }));
    render(<MedicalHistorySummary />);
    const consent = screen.getByRole("checkbox");
    fireEvent.click(consent);
    fireEvent.click(screen.getByRole("button", { name: "Generate AI summary" }));
    expect(await screen.findByText("Old summary")).toBeInTheDocument();
    fireEvent.click(consent);
    fireEvent.click(screen.getByRole("button", { name: "Refresh AI summary" }));
    expect(screen.queryByText("Old summary")).not.toBeInTheDocument();
    expect(consent).toBeDisabled();
    expect(consent).not.toBeChecked();
    reject(new Error("Unavailable"));
    expect(await screen.findByRole("alert")).toHaveTextContent("Unavailable");
    expect(consent).not.toBeChecked();
    expect(screen.getByRole("button", { name: "Generate AI summary" })).toBeDisabled();
  });

  it("does not retain prescription explanations when the selected record changes", async () => {
    mocks.prescription.mockResolvedValue({ plain_language_summary: "First record explanation", medicine_explanations: [], questions_to_ask_clinician: [], disclaimer: "Not medical advice." });
    const view = render(<PrescriptionExplanation prescriptionId="rx-1" />);
    fireEvent.click(screen.getByRole("button", { name: "Explain with AI" }));
    expect(await screen.findByText("First record explanation")).toBeInTheDocument();
    view.rerender(<PrescriptionExplanation prescriptionId="rx-2" />);
    expect(screen.queryByText("First record explanation")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Explain with AI" })).toBeEnabled();
  });

  it("does not attach a late lab response to a newly selected record", async () => {
    let resolve!: (value: unknown) => void;
    mocks.lab.mockImplementation(() => new Promise((resolveRequest) => { resolve = resolveRequest; }));
    const view = render(<LabReportExplanation reportId="report-1" />);
    fireEvent.click(screen.getByRole("button", { name: "Explain with AI" }));
    view.rerender(<LabReportExplanation reportId="report-2" />);
    resolve({ summary: "Old lab explanation", parameter_explanations: [], flagged_results: [], questions_for_clinician: [], disclaimer: "Not a diagnosis." });
    await waitFor(() => expect(screen.getByRole("button", { name: "Explain with AI" })).toBeEnabled());
    expect(screen.queryByText("Old lab explanation")).not.toBeInTheDocument();
  });
});
