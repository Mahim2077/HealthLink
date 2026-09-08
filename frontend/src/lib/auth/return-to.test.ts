import { describe, expect, it } from "vitest";
import { safeReturnTo } from "./return-to";

describe("safe same-portal return destination", () => {
  it("preserves the booking destination", () => {
    expect(safeReturnTo("/citizen/appointments/book?doctor_user_id=123", "CITIZEN")).toBe("/citizen/appointments/book?doctor_user_id=123");
  });
  it.each([null, "https://evil.example", "//evil.example", "/admin/dashboard", "/citizen/../admin/dashboard", "/citizen/\\evil", "/citizen/%2f%2fevil", "/citizen/login"])("rejects unsafe or cross-portal target %s", value => {
    expect(safeReturnTo(value, "CITIZEN")).toBe("/citizen/dashboard");
  });
});
