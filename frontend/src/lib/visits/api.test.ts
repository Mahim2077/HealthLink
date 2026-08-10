import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    get: apiMocks.get,
    post: apiMocks.post,
    put: apiMocks.put,
  },
}));

import {
  listCitizenVisitsToday,
  loadCurrentPatient,
  readCitizenVisit,
  readDoctorVisit,
  startVisitForCurrent,
  updateDoctorVisit,
} from "./api";

describe("Visits API", () => {
  beforeEach(() => {
    apiMocks.get.mockReset();
    apiMocks.post.mockReset();
    apiMocks.put.mockReset();
  });

  it("loads the doctor current-patient view (or null when empty)", async () => {
    apiMocks.get.mockResolvedValue(null);
    await expect(loadCurrentPatient()).resolves.toBeNull();
    expect(apiMocks.get).toHaveBeenCalledWith(
      "doctors/me/visits/current-patient",
    );
  });

  it("starts a visit against the current queue row", async () => {
    apiMocks.post.mockResolvedValue({ id: "visit-1" });
    await expect(startVisitForCurrent("queue-1")).resolves.toEqual({
      id: "visit-1",
    });
    expect(apiMocks.post).toHaveBeenCalledWith(
      "doctors/me/visits/start-for-current/queue-1",
      {},
    );
  });

  it("reads and updates a single doctor visit", async () => {
    apiMocks.get.mockResolvedValue({ id: "visit-1" });
    apiMocks.put.mockResolvedValue({ id: "visit-1", status: "DRAFT" });
    await expect(readDoctorVisit("visit-1")).resolves.toEqual({ id: "visit-1" });
    await expect(
      updateDoctorVisit("visit-1", {
        chief_complaint: "fever",
        diagnosis: "viral",
      }),
    ).resolves.toEqual({ id: "visit-1", status: "DRAFT" });
    expect(apiMocks.get).toHaveBeenCalledWith("doctors/me/visits/visit-1");
    expect(apiMocks.put).toHaveBeenCalledWith(
      "doctors/me/visits/visit-1",
      { chief_complaint: "fever", diagnosis: "viral" },
    );
  });

  it("lists and reads the citizen today visits", async () => {
    apiMocks.get.mockResolvedValue({ visits: [] });
    apiMocks.get.mockResolvedValueOnce({ visits: [] });
    apiMocks.get.mockResolvedValueOnce({ id: "visit-1" });
    await expect(listCitizenVisitsToday()).resolves.toEqual({ visits: [] });
    await expect(readCitizenVisit("visit-1")).resolves.toEqual({ id: "visit-1" });
    expect(apiMocks.get).toHaveBeenNthCalledWith(1, "citizens/me/visits/today");
    expect(apiMocks.get).toHaveBeenNthCalledWith(2, "citizens/me/visits/visit-1");
  });
});
