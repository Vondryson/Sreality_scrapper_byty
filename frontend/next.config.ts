import type { NextConfig } from "next";

const backendUrl = process.env.SREALITY_BACKEND_URL ?? "http://localhost:8000";

if (!/^https?:\/\/[^/]+(?::\d+)?$/.test(backendUrl)) {
  throw new Error("SREALITY_BACKEND_URL must be an absolute HTTP(S) origin without a path");
}

const nextConfig: NextConfig = {
  poweredByHeader: false,
  images: {
    remotePatterns: [{ protocol: "https", hostname: "**.sdn.cz" }],
  },
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
