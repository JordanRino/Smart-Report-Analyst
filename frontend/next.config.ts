import type { NextConfig } from "next";

/**
 * Hostnames (no scheme, no port) that may load `/_next/*` dev assets when the
 * page is opened from a non-localhost URL (e.g. EC2 private IP in the browser).
 * @see https://nextjs.org/docs/app/api-reference/config/next-config-js/allowedDevOrigins
 */
const allowedDevOrigins = (process.env.NEXT_ALLOWED_DEV_ORIGINS ?? "")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);

const nextConfig: NextConfig = {
  allowedDevOrigins,
};

export default nextConfig;
