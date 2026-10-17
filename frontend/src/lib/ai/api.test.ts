import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({ post: vi.fn() }));
vi.mock("@/lib/api/client", () => ({ apiClient: apiMocks }));

import {
  askAi,
  explainLabReport,
  explainPrescription,
  requestSymptomGuidance,
  summarizeMedicalHistory,
} from "./api";

describe("AI API", () => {
  beforeEach(() => vi.clearAllMocks());

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
