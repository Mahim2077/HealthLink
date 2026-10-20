import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ list: vi.fn(), load: vi.fn(), send: vi.fn(), remove: vi.fn(), symptoms: vi.fn() }));
vi.mock("@/lib/ai/api", () => ({ listConversations: mocks.list, loadConversation: mocks.load, sendConversationMessage: mocks.send, deleteConversation: mocks.remove, requestSymptomGuidance: mocks.symptoms }));
import { AiAssistant } from "./ai-assistant";

const summary = { id: "chat-one", title: "What is a reference range?", created_at: "2026-10-18T12:00:00Z", updated_at: "2026-10-18T12:00:00Z" };
const response = { answer: "A range is a guide, not a diagnosis.", record_observations: [], questions_for_clinician: ["How does this relate to my history?"], disclaimer: "Not a diagnosis or prescription.", records_used: {} };
const turn = { id: "turn-one", message: summary.title, mode: "GENERAL", created_at: summary.created_at, response };
const input = () => screen.getByRole("textbox", { name: "Your question" });
const send = () => screen.getByRole("button", { name: "Send message" });
async function records() {
  fireEvent.click(screen.getByRole("button", { name: /General · Records off/ }));
  fireEvent.click(screen.getByRole("radio", { name: "Use my records" }));
}
describe("Saved AI conversations", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.list.mockResolvedValue({ items: [], next_offset: null });
    mocks.send.mockResolvedValue({ conversation: summary, turn });
    mocks.remove.mockResolvedValue(undefined);
    mocks.load.mockResolvedValue({ ...summary, turns: [turn] });
  });

  it("keeps a transcript across questions and starts a clean conversation", async () => {
    render(<AiAssistant />);
    fireEvent.change(input(), { target: { value: summary.title } });
    fireEvent.click(send());
    expect(await screen.findByText(response.answer)).toBeInTheDocument();
    expect(mocks.send).toHaveBeenCalledWith(expect.objectContaining({ mode: "GENERAL", message: summary.title, use_my_health_records: false, conversation_id: null, client_request_id: expect.any(String) }), expect.any(AbortSignal));
    fireEvent.change(input(), { target: { value: "Explain more simply." } });
    expect(screen.getByText(response.answer)).toBeInTheDocument();
    mocks.send.mockResolvedValue({ conversation: summary, turn: { ...turn, id: "turn-two", message: "Explain more simply.", response: { ...response, answer: "Here is a simpler explanation." } } });
    fireEvent.click(send());
    expect(await screen.findByText("Here is a simpler explanation.")).toBeInTheDocument();
    expect(screen.getByText(response.answer)).toBeInTheDocument();
    expect(mocks.send.mock.calls[1][0].conversation_id).toBe(summary.id);
    fireEvent.click(screen.getByRole("button", { name: "New conversation" }));
    expect(screen.queryByText(response.answer)).not.toBeInTheDocument();
    expect(input()).toHaveValue("");
    expect(screen.getByRole("button", { name: /General · Records off/ })).toBeInTheDocument();
  });

  it("requires fresh records consent and defaults back to General after sending", async () => {
    mocks.send.mockResolvedValue({ conversation: summary, turn: { ...turn, mode: "RECORD_AWARE" } });
    render(<AiAssistant />);
    fireEvent.change(input(), { target: { value: summary.title } });
    await records();
    expect(send()).toBeDisabled();
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.change(input(), { target: { value: summary.title + " please" } });
    expect(screen.getByRole("checkbox")).not.toBeChecked();
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(send());
    expect(await screen.findByText(response.answer)).toBeInTheDocument();
    expect(mocks.send.mock.calls[0][0]).toMatchObject({ mode: "RECORD_AWARE", use_my_health_records: true });
    expect(screen.getByRole("button", { name: /General · Records off/ })).toBeInTheDocument();
  });

  it("preserves failed questions and reuses the retry ID without retaining consent", async () => {
    mocks.send.mockRejectedValueOnce(new Error("Temporarily unavailable"));
    render(<AiAssistant />);
    fireEvent.change(input(), { target: { value: summary.title } });
    await records();
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(send());
    expect(await screen.findByRole("alert")).toHaveTextContent("Temporarily unavailable");
    expect(input()).toHaveValue(summary.title);
    expect(screen.getByRole("checkbox")).not.toBeChecked();
    expect(send()).toBeDisabled();
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(send());
    expect(await screen.findByText(response.answer)).toBeInTheDocument();
    expect(mocks.send.mock.calls[0][0].client_request_id).toBe(mocks.send.mock.calls[1][0].client_request_id);
  });

  it("loads history and confirms deletion before removing it", async () => {
    mocks.list.mockResolvedValue({ items: [summary], next_offset: null });
    render(<AiAssistant />);
    const history = screen.getByRole("complementary", { name: "Conversation history" });
    fireEvent.click(await within(history).findByRole("button", { name: /^What is a reference range/ }));
    expect(await screen.findByText(response.answer)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Delete conversation:/ }));
    expect(mocks.remove).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Delete conversation:/ }));
    fireEvent.click(screen.getByRole("button", { name: "Delete permanently" }));
    await waitFor(() => expect(mocks.remove).toHaveBeenCalledWith(summary.id));
    await waitFor(() => expect(screen.queryByText(response.answer)).not.toBeInTheDocument());
  });

  it("preserves chat when opening and closing symptom guidance", async () => {
    mocks.symptoms.mockResolvedValue({ symptom_summary: "A brief summary.", general_information: [], red_flags: ["Trouble breathing"], suggested_next_step: "Contact a clinician.", urgency_category: "PROMPT_CLINICAL_REVIEW", disclaimer: "Not a diagnosis." });
    render(<AiAssistant />);
    fireEvent.change(input(), { target: { value: summary.title } });
    fireEvent.click(send());
    await screen.findByText(response.answer);
    fireEvent.click(screen.getByRole("button", { name: "Symptom guidance" }));
    fireEvent.change(screen.getByLabelText("Describe your symptoms"), { target: { value: "Cough for two days" } });
    fireEvent.click(screen.getByRole("button", { name: "Get general guidance" }));
    expect(await screen.findByText("Trouble breathing")).toBeInTheDocument();
    expect(mocks.symptoms).toHaveBeenCalledWith("Cough for two days");
    fireEvent.click(screen.getByRole("button", { name: "Back to chat" }));
    expect(screen.getByText(response.answer)).toBeInTheDocument();
  });

  it("disables context/navigation during generation and ignores unmounted responses", async () => {
    let resolve!: (value: unknown) => void;
    mocks.send.mockImplementation(() => new Promise(done => { resolve = done; }));
    const view = render(<AiAssistant />);
    fireEvent.change(input(), { target: { value: summary.title } });
    fireEvent.click(send());
    expect(input()).toBeDisabled();
    expect(screen.getByRole("button", { name: "New conversation" })).toBeDisabled();
    expect(screen.getByRole("button", { name: /General · Records off/ })).toBeDisabled();
    view.unmount();
    await act(async () => resolve({ conversation: summary, turn }));
  });

  it("retries history loading and rejects short whitespace-only questions", async () => {
    mocks.list.mockRejectedValueOnce(new Error("History unavailable"));
    render(<AiAssistant />);
    expect(await screen.findByRole("alert")).toHaveTextContent("History unavailable");
    fireEvent.click(screen.getByRole("button", { name: "Retry history" }));
    await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());
    fireEvent.change(input(), { target: { value: " a " } });
    expect(send()).toBeDisabled();
  });
});
