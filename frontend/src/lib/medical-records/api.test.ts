import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({ get: vi.fn() }));

vi.mock("@/lib/api/client", () => ({
  apiClient: { get: apiMocks.get },
}));

import {
  listCitizenMedicalHistory,
  listCurrentPatientMedicalHistory,
} from "./api";

describe("Medical history API", () => {
  beforeEach(() => apiMocks.get.mockReset());

  it("serializes bounded citizen filters", async () => {
    apiMocks.get.mockResolvedValue({ items: [] });
    await listCitizenMedicalHistory({
      resource_type: "VISIT",
      date_from: "2026-08-01",
      date_to: "2026-08-31",
      page: 2,
      page_size: 10,
    });
    expect(apiMocks.get).toHaveBeenCalledWith(
      "citizens/me/medical-history?resource_type=VISIT&date_from=2026-08-01&date_to=2026-08-31&page=2&page_size=10",
    );
  });

  it("uses the current-patient professional endpoint", async () => {
    apiMocks.get.mockResolvedValue({ items: [] });
    await listCurrentPatientMedicalHistory();
    expect(apiMocks.get).toHaveBeenCalledWith(
      "professionals/current-patient/medical-history",
    );
  });
});
