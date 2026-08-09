import { describe, expect, it } from "vitest";

import { joinApiUrl, normalizeApiBaseUrl } from "./config";

describe("API configuration", () => {
  it("normalizes a valid API base URL", () => {
    expect(normalizeApiBaseUrl(" https://api.healthlink.test/api/v1/// ")).toBe(
      "https://api.healthlink.test/api/v1",
    );
  });

  it("joins API paths without duplicate separators", () => {
    expect(
      joinApiUrl("https://api.healthlink.test/api/v1/", "/health"),
    ).toBe("https://api.healthlink.test/api/v1/health");
  });

  it("rejects relative or non-HTTP API locations", () => {
    expect(() => normalizeApiBaseUrl("/api/v1")).toThrow(
      "must be a valid absolute URL",
    );
    expect(() => normalizeApiBaseUrl("file:///api/v1")).toThrow(
      "must use HTTP or HTTPS",
    );
  });
});
