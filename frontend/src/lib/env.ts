/**
 * Public API origin (no trailing slash). Used for REST and CopilotKit runtime URLs.
 * Prefer NEXT_PUBLIC_API_BASE_URL; NEXT_PUBLIC_API_URL may be a full /api prefix for backwards compatibility.
 */
export function getPublicApiBase(): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "");
  if (base) return base;

  const legacy = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
  if (legacy) {
    // e.g. http://localhost:8000/api -> http://localhost:8000
    return legacy.replace(/\/api\/?$/, "") || "http://localhost:8000";
  }

  return "http://localhost:8000";
}

export function getApiPrefix(): string {
  return `${getPublicApiBase()}/api`;
}

export function getCopilotRuntimeUrl(): string {
  return `${getPublicApiBase()}/api/copilotkit`;
}
