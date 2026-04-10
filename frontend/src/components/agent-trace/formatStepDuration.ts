/** Human-readable duration for trace UI (milliseconds). */
export function formatStepDuration(ms: number): string {
  if (!Number.isFinite(ms) || ms < 0) {
    return "—";
  }
  if (ms < 1000) {
    return `${Math.round(ms)} ms`;
  }
  const s = ms / 1000;
  if (s < 60) {
    return `${s.toFixed(s >= 10 ? 0 : 1)} s`;
  }
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}m ${r < 10 ? r.toFixed(1) : Math.round(r)}s`;
}
