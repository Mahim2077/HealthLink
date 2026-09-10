import type { NextConfig } from "next";

const localBackendOrigin = (
  process.env.HEALTHLINK_BACKEND_ORIGIN ?? "http://127.0.0.1:8000"
).replace(/\/+$/, "");

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1"],
  poweredByHeader: false,
  reactStrictMode: true,
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
