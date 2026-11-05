import { describe, expect, it } from "vitest";

import { facilityOptionLabels } from "./presentation";

describe("facilityOptionLabels", () => {
  it("uses locality and public registration details to distinguish same-name facilities", () => {
    const labels = facilityOptionLabels([
      { id: "private-id-a", name: "City Hospital", area: "Savar, Dhaka", address: "North Road", registration_number: "HOSP-101" },
      { id: "private-id-b", name: "City Hospital", area: "Savar, Dhaka", address: "South Road", registration_number: "HOSP-202" },
      { id: "private-id-c", name: "River Clinic", area: "Raozan, Chattogram", registration_number: "CL-3" },
    ]);
    expect(labels.get("private-id-a")).toBe("City Hospital · Savar, Dhaka · North Road · Registration HOSP-101");
    expect(labels.get("private-id-b")).toContain("South Road · Registration HOSP-202");
    expect(labels.get("private-id-c")).toBe("River Clinic · Raozan, Chattogram");
    expect([...labels.values()].join(" ")).not.toContain("private-id");
  });

  it("uses address when locality is missing and flags otherwise indistinguishable listings", () => {
    const labels = facilityOptionLabels([
      { id: "a", name: "Shared Clinic", address: "Station Road" },
      { id: "b", name: "Shared Clinic", address: "Station Road" },
      { id: "c", name: "Shared Clinic", address: "Market Road" },
    ]);
    expect(labels.get("a")).toBe("Shared Clinic · Station Road · Listing 1 (details need confirmation)");
    expect(labels.get("b")).toContain("Listing 2 (details need confirmation)");
    expect(labels.get("c")).toBe("Shared Clinic · Market Road");
  });
});
