import { describe, expect, it } from "vitest";

import { joinApiUrl, normalizeApiBaseUrl } from "./config";

describe("API configuration", () => {
  it("normalizes a valid API base URL", () => {
    expect(normalizeApiBaseUrl(" https://api.healthlink.test/api/v1/// ")).toBe(
      "https://api.healthlink.test/api/v1",
    );
  });

  it("accepts a same-origin API path for a combined deployment", () => {
    expect(normalizeApiBaseUrl(" /api/v1/// ")).toBe("/api/v1");
    expect(joinApiUrl("/api/v1/", "/health")).toBe("/api/v1/health");
  });

  it("joins API paths without duplicate separators", () => {
    expect(
      joinApiUrl("https://api.healthlink.test/api/v1/", "/health"),
    ).toBe("https://api.healthlink.test/api/v1/health");
  });

  it("rejects unsafe relative or non-HTTP API locations", () => {
    expect(() => normalizeApiBaseUrl("api/v1")).toThrow(
      "must be an HTTP(S) URL or a root-relative path",
    );
    expect(() => normalizeApiBaseUrl("//example.test/api/v1")).toThrow();
    expect(() => normalizeApiBaseUrl("file:///api/v1")).toThrow(
      "must use HTTP or HTTPS",
    );
  });
});
