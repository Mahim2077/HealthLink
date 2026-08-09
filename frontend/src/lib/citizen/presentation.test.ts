import { describe, expect, it } from "vitest";

import { formatCitizenDate, maskIdentityValue } from "./presentation";

describe("Citizen presentation utilities", () => {
  it("masks identity values while retaining a recognizable suffix", () => {
    const rawIdentity = "00123456789012345";
    const masked = maskIdentityValue(rawIdentity);

    expect(masked).toContain("2345");
    expect(masked).not.toContain(rawIdentity);
    expect(masked).toMatch(/^•+/);
  });

  it("never reveals short identity values", () => {
    for (const rawIdentity of ["1", "01", "A-1", "0001"]) {
      const masked = maskIdentityValue(rawIdentity);

      expect(masked).not.toContain(rawIdentity);
      expect(masked).toMatch(/^•{4}$/);
    }
  });

  it("formats profile dates for display", () => {
    const formatted = formatCitizenDate("1990-01-02");

    expect(formatted).toContain("2");
    expect(formatted).toContain("January");
    expect(formatted).toContain("1990");
  });
});
