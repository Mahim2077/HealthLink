import type { NextConfig } from "next";

const localBackendOrigin = (
  process.env.HEALTHLINK_BACKEND_ORIGIN ?? "http://127.0.0.1:8000"
).replace(/\/+$/, "");

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1"],
  poweredByHeader: false,
  reactStrictMode: true,
  async headers() {
    return [{
      source: "/:path*",
      headers: [
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "X-Frame-Options", value: "SAMEORIGIN" },
        { key: "Referrer-Policy", value: "same-origin" },
        { key: "Permissions-Policy", value: "geolocation=(self), camera=(), microphone=()" },
        // Keep same-origin PDF previews and Next's scripts/styles working. A
        // stricter script policy needs a separately tested nonce/hash strategy.
        { key: "Content-Security-Policy", value: "base-uri 'self'; form-action 'self'; frame-ancestors 'self'" },
      ],
    }];
  },
  async rewrites() {
    if (process.env.NODE_ENV !== "development") {
      return [];
    }

    return [
      {
        source: "/api/v1/:path*",
        destination: `${localBackendOrigin}/api/v1/:path*`,
      },
      {
        source: "/health",
        destination: `${localBackendOrigin}/health`,
      },
    ];
  },
};

export default nextConfig;
