import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  poweredByHeader: false,
  // Keep isolated browser tests from taking over the developer's running server.
  distDir: process.env.PLAYWRIGHT_DEV_SERVER ? ".next/playwright" : ".next",
};

export default nextConfig;
