/** Matches ``[[trace:123ms]] `` prefix from AG-UI reasoning deltas (elapsed ms since turn trace start). */
const TRACE_PREFIX = /^\[\[trace:(\d+)ms\]\] /;

export type ParsedTraceLine =
  | { kind: "elapsed"; elapsedMs: number; body: string }
  | { kind: "plain"; body: string };

export function parseTraceLine(line: string): ParsedTraceLine {
  const m = line.match(TRACE_PREFIX);
  if (!m) {
    return { kind: "plain", body: line };
  }
  const elapsedMs = Number.parseInt(m[1] ?? "", 10);
  if (!Number.isFinite(elapsedMs)) {
    return { kind: "plain", body: line };
  }
  return { kind: "elapsed", elapsedMs, body: line.slice(m[0].length) };
}
