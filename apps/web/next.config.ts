import type { NextConfig } from "next";

/** Upstream FastAPI origin for dev/proxy rewrites (server-side). See CLOUDOPT_API_ORIGIN in .env.example */
const apiOrigin =
  process.env.CLOUDOPT_API_ORIGIN?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${apiOrigin}/api/:path*` },
      { source: "/health", destination: `${apiOrigin}/health` },
      { source: "/health/:path*", destination: `${apiOrigin}/health/:path*` },
      { source: "/openapi.json", destination: `${apiOrigin}/openapi.json` },
      { source: "/docs", destination: `${apiOrigin}/docs` },
      { source: "/docs/:path*", destination: `${apiOrigin}/docs/:path*` },
      { source: "/redoc", destination: `${apiOrigin}/redoc` },
    ];
  },
};

export default nextConfig;
