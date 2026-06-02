import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // @xyflow/react renders [children, conditionalElement] without keys internally.
  // Strict mode's double-render exposes this library bug as a console warning.
  // Remove this once @xyflow/react fixes the issue upstream.
  reactStrictMode: false,
};

export default nextConfig;
