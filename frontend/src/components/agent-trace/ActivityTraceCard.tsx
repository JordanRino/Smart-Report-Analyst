"use client";

import type { ActivityMessage } from "@copilotkit/shared";
import { useMemo, useState } from "react";

import { TOOL_TRACE_ACTIVITY_TYPE } from "./constants";
import { formatStepDuration } from "./formatStepDuration";

type Props = {
  message: ActivityMessage;
  inProgress?: boolean;
};

type TraceContent = {
  lines?: unknown;
  openSteps?: unknown;
  timings?: unknown;
};

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

export function ActivityTraceCard({ message, inProgress }: Props) {
  const [open, setOpen] = useState(false);

  const parsed = useMemo(() => {
    const c = message.content as TraceContent;
    const lines = Array.isArray(c?.lines)
      ? (c.lines as unknown[]).map((x) => String(x))
      : [];
    const openSteps = Array.isArray(c?.openSteps)
      ? (c.openSteps as unknown[]).map((x) => String(x))
      : [];
    const timings = Array.isArray(c?.timings)
      ? (c.timings as unknown[]).filter(isRecord)
      : [];
    return { lines, openSteps, timings };
  }, [message.content]);

  const preview = useMemo(() => {
    const tail = parsed.lines.filter((l) => l.trim().length > 0).slice(-1)[0] ?? "";
    const line = tail.trim();
    return line.length > 120 ? `${line.slice(0, 117)}…` : line || "Working…";
  }, [parsed.lines]);

  if (message.activityType !== TOOL_TRACE_ACTIVITY_TYPE) {
    return null;
  }

  return (
    <details
      open={open}
      onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}
      className="mb-2 rounded-lg border border-sky-200/90 bg-sky-50/80 text-sm text-sky-950 dark:border-sky-800 dark:bg-sky-950/40 dark:text-sky-100"
    >
      <summary className="cursor-pointer select-none list-none px-3 py-2 font-medium [&::-webkit-details-marker]:hidden">
        <span className="inline-flex items-center gap-2">
          <span className="text-sky-700 dark:text-sky-300">Trace</span>
          <span className="font-normal text-sky-900/90 dark:text-sky-100/90">{preview}</span>
          {inProgress ? (
            <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-sky-500" />
          ) : null}
        </span>
      </summary>
      <div className="border-t border-sky-200/90 px-3 py-2 dark:border-sky-800">
        {parsed.openSteps.length > 0 ? (
          <p className="mb-2 text-xs text-sky-800/90 dark:text-sky-200/90">
            Running: {parsed.openSteps.join(", ")}
          </p>
        ) : null}
        <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-words font-mono text-xs leading-relaxed text-sky-900 dark:text-sky-100">
          {parsed.lines.length > 0 ? parsed.lines.join("\n") : "—"}
        </pre>
        {parsed.timings.length > 0 ? (
          <ul className="mt-2 space-y-1 text-xs text-sky-800/85 dark:text-sky-200/85">
            {parsed.timings.map((row, i) => {
              const tool = typeof row.tool === "string" ? row.tool : "tool";
              const ms = typeof row.duration_ms === "number" ? row.duration_ms : null;
              return (
                <li key={`${tool}-${i}`}>
                  {tool}
                  {ms != null ? ` · ${formatStepDuration(ms)}` : null}
                </li>
              );
            })}
          </ul>
        ) : null}
      </div>
    </details>
  );
}
