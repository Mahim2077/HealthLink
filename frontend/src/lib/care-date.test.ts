import { describe, expect, it } from "vitest";
import { careDate } from "./care-date";

describe("Bangladesh care date", () => {
  it("changes dates at Dhaka midnight, not UTC midnight", () => {
    expect(careDate(new Date("2026-09-08T17:59:59Z"))).toBe("2026-09-08");
    expect(careDate(new Date("2026-09-08T18:00:00Z"))).toBe("2026-09-09");
  });
});
