import { expect, it } from "vitest";
import nextConfig from "./next.config";

it("applies baseline response protection without disabling same-origin GPS or PDF frames", async () => {
  const rules = await nextConfig.headers!();
  expect(rules).toHaveLength(1);
  expect(rules[0].source).toBe("/:path*");
  const headers = Object.fromEntries(rules[0].headers.map(({ key, value }) => [key, value]));
  expect(headers).toMatchObject({
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "Referrer-Policy": "same-origin",
    "Permissions-Policy": "geolocation=(self), camera=(), microphone=()",
  });
  expect(headers["Content-Security-Policy"]).toContain("frame-ancestors 'self'");
  expect(headers["Content-Security-Policy"]).not.toContain("default-src");
});
