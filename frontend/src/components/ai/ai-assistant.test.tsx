import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ ask: vi.fn(), symptoms: vi.fn() }));
vi.mock("@/lib/ai/api", () => ({ askAi: mocks.ask, requestSymptomGuidance: mocks.symptoms }));

import { AiAssistant } from "./ai-assistant";

describe("AiAssistant", () => {
  beforeEach(() => vi.clearAllMocks());

  it("requires explicit consent before record-aware chat", async () => {
    mocks.ask.mockResolvedValue({ answer: "Bring your recent reports.", record_observations: [], questions_for_clinician: [], disclaimer: "Informational only.", records_used: {} });
    render(<AiAssistant />);
    fireEvent.click(screen.getByText("Use my records"));
    fireEvent.change(screen.getByLabelText("Your question"), { target: { value: "What should I discuss?" } });
    expect(screen.getByRole("button", { name: "Ask HealthLink AI" })).toBeDisabled();
    fireEvent.click(screen.getByText(/I allow HealthLink AI/));
    fireEvent.click(screen.getByRole("button", { name: "Ask HealthLink AI" }));
    await waitFor(() => expect(mocks.ask).toHaveBeenCalledWith({ mode: "RECORD_AWARE", message: "What should I discuss?", use_my_health_records: true }));
    expect(await screen.findByText("Bring your recent reports.")).toBeInTheDocument();
  });

  it("shows red flags and urgency without requesting records", async () => {
    mocks.symptoms.mockResolvedValue({ symptom_summary: "A brief summary.", general_information: ["Rest if able."], red_flags: ["Trouble breathing"], suggested_next_step: "Contact a clinician.", urgency_category: "PROMPT_CLINICAL_REVIEW", disclaimer: "Not a diagnosis." });
    render(<AiAssistant />);
    fireEvent.click(screen.getByRole("tab", { name: /symptom guidance/i }));
    fireEvent.change(screen.getByLabelText("Describe your symptoms"), { target: { value: "Cough for two days" } });
    fireEvent.click(screen.getByRole("button", { name: "Get general guidance" }));
    expect(await screen.findByText("Trouble breathing")).toBeInTheDocument();
    expect(screen.getByText("Prompt clinician review")).toBeInTheDocument();
    expect(mocks.symptoms).toHaveBeenCalledWith("Cough for two days");
  });

  it("consumes consent on failed requests and disables pending context changes", async () => {
    let reject!: (reason: Error) => void;
    mocks.ask.mockImplementation(() => new Promise((_, rejectRequest) => { reject = rejectRequest; }));
    render(<AiAssistant />);
    fireEvent.click(screen.getByText("Use my records"));
    fireEvent.change(screen.getByLabelText("Your question"), { target: { value: "What should I ask?" } });
    const consent = screen.getByRole("checkbox");
    fireEvent.click(consent);
    fireEvent.click(screen.getByRole("button", { name: "Ask HealthLink AI" }));
    expect(consent).not.toBeChecked();
    expect(consent).toBeDisabled();
    expect(screen.getByLabelText("Your question")).toBeDisabled();
    screen.getAllByRole("radio").forEach((radio) => expect(radio).toBeDisabled());
    reject(new Error("Temporarily unavailable"));
    expect(await screen.findByRole("alert")).toHaveTextContent("Temporarily unavailable");
    expect(consent).not.toBeChecked();
    expect(screen.getByRole("button", { name: "Ask HealthLink AI" })).toBeDisabled();
  });

  it("clears previous responses on question and context changes", async () => {
    mocks.ask.mockResolvedValue({ answer: "A temporary answer", record_observations: [], questions_for_clinician: [], disclaimer: "Informational only.", records_used: {} });
    render(<AiAssistant />);
    const input = screen.getByLabelText("Your question");
    fireEvent.change(input, { target: { value: "First question" } });
    fireEvent.click(screen.getByRole("button", { name: "Ask HealthLink AI" }));
    expect(await screen.findByText("A temporary answer")).toBeInTheDocument();
    fireEvent.change(input, { target: { value: "Second question" } });
    expect(screen.queryByText("A temporary answer")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Ask HealthLink AI" }));
    expect(await screen.findByText("A temporary answer")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Use my records"));
    expect(screen.queryByText("A temporary answer")).not.toBeInTheDocument();
  });

  it("supports keyboard tabs and requires three trimmed input characters", () => {
    render(<AiAssistant />);
    fireEvent.change(screen.getByLabelText("Your question"), { target: { value: " a " } });
    expect(screen.getByRole("button", { name: "Ask HealthLink AI" })).toBeDisabled();
    const chat = screen.getByRole("tab", { name: /ask healthlink ai/i });
    fireEvent.keyDown(chat, { key: "End" });
    const symptoms = screen.getByRole("tab", { name: /symptom guidance/i });
    expect(symptoms).toHaveFocus();
    expect(symptoms).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel")).toHaveAttribute("aria-labelledby", symptoms.id);
    expect(symptoms.getAttribute("aria-controls")).toBe(screen.getByRole("tabpanel").id);
    expect(screen.getByText(/Do not wait for an AI response/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Describe your symptoms"), { target: { value: "ab" } });
    expect(screen.getByRole("button", { name: "Get general guidance" })).toBeDisabled();
    fireEvent.keyDown(symptoms, { key: "ArrowRight" });
    expect(chat).toHaveFocus();
    expect(chat).toHaveAttribute("aria-selected", "true");
    fireEvent.keyDown(chat, { key: "ArrowLeft" });
    expect(symptoms).toHaveFocus();
    fireEvent.keyDown(symptoms, { key: "Home" });
    expect(chat).toHaveFocus();
  });
});
