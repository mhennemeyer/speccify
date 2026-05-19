import type { NextConfig } from "next";

/**
 * Phase 1d Browser-Playground.
 *
 * - `reactStrictMode` on by default (catches double-render bugs early).
 * - In dev, `/api/v1/*` is proxied to the FastAPI backend on
 *   `http://localhost:8000` so the browser stays on the Next origin and CORS
 *   stays simple. Override via `SPECCIFY_BACKEND_URL` for non-default ports.
 */

const backendUrl = process.env.SPECCIFY_BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendUrl}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
