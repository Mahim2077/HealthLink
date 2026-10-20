import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({ post: vi.fn(), get: vi.fn(), delete: vi.fn() }));
vi.mock("@/lib/api/client", () => ({ apiClient: apiMocks }));

import {
  askAi,
  explainLabReport,
  explainPrescription,
  requestSymptomGuidance,
  summarizeMedicalHistory,
  listConversations,
  loadConversation,
  deleteConversation,
  sendConversationMessage,
} from "./api";

describe("AI API", () => {
  beforeEach(() => vi.clearAllMocks());

  it("uses private conversation routes without putting question text in URLs", async () => {
    const controller = new AbortController();
    await listConversations(30, controller.signal);
    await loadConversation("chat/one", controller.signal);
    await deleteConversation("chat/one");
    const body = { conversation_id: null, client_request_id: "request-one", mode: "GENERAL" as const, message: "A private question", use_my_health_records: false };
    await sendConversationMessage(body, controller.signal);
    expect(apiMocks.get).toHaveBeenNthCalledWith(1, "ai/conversations?offset=30", { cache: "no-store", signal: controller.signal });
    expect(apiMocks.get).toHaveBeenNthCalledWith(2, "ai/conversations/chat%2Fone", { cache: "no-store", signal: controller.signal });
    expect(apiMocks.delete).toHaveBeenCalledWith("ai/conversations/chat%2Fone");
    expect(apiMocks.post).toHaveBeenCalledWith("ai/conversation-messages", body, { signal: controller.signal });
  });

  it("uses encoded record routes and explicit medical-record consent", async () => {
    apiMocks.post.mockResolvedValue({});
    await explainPrescription("rx/one");
    await explainLabReport("report/one");
    await summarizeMedicalHistory();
    expect(apiMocks.post).toHaveBeenNthCalledWith(1, "ai/prescriptions/rx%2Fone/explain");
    expect(apiMocks.post).toHaveBeenNthCalledWith(2, "ai/lab-reports/report%2Fone/explain");
    expect(apiMocks.post).toHaveBeenNthCalledWith(3, "ai/medical-history/summary", { use_my_health_records: true });
  });

  it("sends the selected chat mode and symptom text", async () => {
    apiMocks.post.mockResolvedValue({});
    await askAi({ mode: "RECORD_AWARE", message: "What should I ask?", use_my_health_records: true });
    await requestSymptomGuidance("Sore throat for two days");
    expect(apiMocks.post).toHaveBeenNthCalledWith(1, "ai/chat", { mode: "RECORD_AWARE", message: "What should I ask?", use_my_health_records: true });
    expect(apiMocks.post).toHaveBeenNthCalledWith(2, "ai/symptom-guidance", { symptoms: "Sore throat for two days" });
  });
});
