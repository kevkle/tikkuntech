import type { NextConfig } from "next";

// Rewrites are resolved at build time, so BACKEND_URL must be set during `next build`.
const backendUrl = process.env.BACKEND_URL ?? "http://backend:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backendUrl}/:path*` }];
  },
};

export default nextConfig;
