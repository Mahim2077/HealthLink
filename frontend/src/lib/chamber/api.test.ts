import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    get: apiMocks.get,
    post: apiMocks.post,
  },
}));

import {
  actOnCurrentPatient,
  callNextPatient,
  finishChamberSession,
  loadChamberSession,
  removeQueueEntry,
  startChamberSession,
} from "./api";

describe("Chamber API", () => {
  beforeEach(() => {
    apiMocks.get.mockReset();
    apiMocks.post.mockReset();
  });

  it("loads today's chamber session with facility_id and optional date", async () => {
    const view = {
      current: null,
      facility_id: "facility-1",
      facility_name: "City Hospital",
      finished: [],
      id: "session-1",
      session_date: "2026-08-10",
      started_at: null,
      ended_at: null,
      status: "OPEN" as const,
      waiting: [],
    };
    apiMocks.get.mockResolvedValue(view);
    await expect(
      loadChamberSession("facility-1", "2026-08-10"),
    ).resolves.toEqual(view);
    expect(apiMocks.get).toHaveBeenCalledWith(
      "professionals/chamber/sessions/today?facility_id=facility-1&session_date=2026-08-10",
    );
  });

  it("omits session_date from the load query when not supplied", async () => {
    apiMocks.get.mockResolvedValue(null);
    await expect(loadChamberSession("facility-1", null)).resolves.toBeNull();
    expect(apiMocks.get).toHaveBeenCalledWith(
      "professionals/chamber/sessions/today?facility_id=facility-1",
    );
  });

  it("starts the chamber session with the supplied payload", async () => {
    const view = {
      current: null,
      facility_id: "facility-1",
      facility_name: "City Hospital",
      finished: [],
      id: "session-1",
      session_date: "2026-08-10",
      started_at: "2026-08-10T09:00:00Z",
      ended_at: null,
      status: "OPEN" as const,
      waiting: [],
    };
    apiMocks.post.mockResolvedValue(view);
    await expect(
      startChamberSession({
        facility_id: "facility-1",
        session_date: "2026-08-10",
      }),
    ).resolves.toEqual(view);
    expect(apiMocks.post).toHaveBeenCalledWith(
      "professionals/chamber/sessions/start",
      { facility_id: "facility-1", session_date: "2026-08-10" },
    );
  });

  it("calls next with facility and date query string", async () => {
    apiMocks.post.mockResolvedValue({});
    await expect(
      callNextPatient("facility-1", "2026-08-10"),
    ).resolves.toEqual({});
    expect(apiMocks.post).toHaveBeenCalledWith(
      "professionals/chamber/queue/call-next?facility_id=facility-1&session_date=2026-08-10",
      {},
    );
  });

  it("posts to the right action endpoint for complete/skip/no-show", async () => {
    apiMocks.post.mockResolvedValue({});
    await actOnCurrentPatient("queue-1", "complete");
    await actOnCurrentPatient("queue-1", "skip");
    await actOnCurrentPatient("queue-1", "no-show");
    expect(apiMocks.post).toHaveBeenNthCalledWith(
      1,
      "professionals/chamber/queue/queue-1/complete",
      {},
    );
    expect(apiMocks.post).toHaveBeenNthCalledWith(
      2,
      "professionals/chamber/queue/queue-1/skip",
      {},
    );
    expect(apiMocks.post).toHaveBeenNthCalledWith(
      3,
      "professionals/chamber/queue/queue-1/no-show",
      {},
    );
  });

  it("removes a queue entry by id", async () => {
    apiMocks.post.mockResolvedValue({});
    await expect(removeQueueEntry("queue-1")).resolves.toEqual({});
    expect(apiMocks.post).toHaveBeenCalledWith(
      "professionals/chamber/queue/queue-1/remove",
      {},
    );
  });

  it("finishes the chamber session with the supplied facility and date", async () => {
    const finish = {
      ended_at: "2026-08-10T17:00:00Z",
      facility_id: "facility-1",
      id: "session-1",
      remaining_waiting: 0,
      session_date: "2026-08-10",
      started_at: "2026-08-10T09:00:00Z",
      status: "FINISHED" as const,
    };
    apiMocks.post.mockResolvedValue(finish);
    await expect(
      finishChamberSession("facility-1", "2026-08-10"),
    ).resolves.toEqual(finish);
    expect(apiMocks.post).toHaveBeenCalledWith(
      "professionals/chamber/sessions/finish?facility_id=facility-1&session_date=2026-08-10",
      {},
    );
  });
});