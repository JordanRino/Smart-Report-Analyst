"use client";

import type { ReasoningMessage } from "@copilotkit/shared";
import { useState } from "react";
import { parseTraceLine } from "@/components/agent-trace/parseTraceLinePrefix";
import { TraceClockIcon } from "@/components/agent-trace/TraceClockIcon";

type Props = {
  message: ReasoningMessage;
  /** True while this reasoning block belongs to the in-flight assistant turn */
  inProgress?: boolean;
};

function TraceLineRow({ line }: { line: string }) {
  const parsed = parseTraceLine(line);
  if (parsed.kind === "plain") {
    return (
      <div className="whitespace-pre-wrap break-words">
        {parsed.body || "\u00a0"}
      </div>
    );
  }
  return (
    <div className="flex flex-wrap items-baseline gap-x-1.5 gap-y-0.5 whitespace-pre-wrap break-words">
      <span
        className="inline-flex shrink-0 items-center gap-0.5 text-zinc-500 dark:text-zinc-400"
        title={`${parsed.elapsedMs} ms since trace start`}
      >
        <TraceClockIcon className="shrink-0 opacity-80" />
        <span className="tabular-nums">{parsed.elapsedMs} ms</span>
      </span>
      <span className="min-w-0 flex-1 text-zinc-700 dark:text-zinc-300">
        {parsed.body}
      </span>
    </div>
  );
}

export function ReasoningTraceMessage({ message, inProgress }: Props) {
  const [open, setOpen] = useState(false);
  const raw = message.content || "—";
  const lines: string[] = raw === "—" ? ["—"] : raw.split("\n");

  return (
    <details
      open={open}
      onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}
      className="mb-2 rounded-lg border border-zinc-200 bg-zinc-50/90 text-sm text-zinc-800 dark:border-zinc-700 dark:bg-zinc-900/60 dark:text-zinc-200"
    >
      <summary className="cursor-pointer select-none list-none px-3 py-2 font-medium [&::-webkit-details-marker]:hidden">
        <span className="inline-flex items-center gap-2">
          <span className="text-zinc-500 dark:text-zinc-400">Trace</span>
          {inProgress ? (
            <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
          ) : null}
        </span>
      </summary>
      <div className="border-t border-zinc-200 px-3 py-2 dark:border-zinc-700">
        <div className="max-h-64 space-y-0.5 overflow-auto font-mono text-xs leading-relaxed">
          {lines.map((line, i) => (
            <TraceLineRow key={i} line={line} />
          ))}
        </div>
        <p className="mt-2 text-xs text-zinc-500 dark:text-zinc-500">
          Clock + ms is elapsed time since the first trace line of this turn (server). Token counts are from
          Bedrock.
        </p>
      </div>
    </details>
  );
}
