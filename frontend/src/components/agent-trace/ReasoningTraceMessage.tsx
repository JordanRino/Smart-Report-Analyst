"use client";

import type { ReasoningMessage } from "@copilotkit/shared";
import { useMemo, useState } from "react";

type Props = {
  message: ReasoningMessage;
  /** True while this reasoning block belongs to the in-flight assistant turn */
  inProgress?: boolean;
};

export function ReasoningTraceMessage({ message, inProgress }: Props) {
  const [open, setOpen] = useState(false);
  const preview = useMemo(() => {
    const t = message.content?.trim() ?? "";
    const line = t.split("\n").find((line: string) => line.trim().length > 0) ?? "";
    return line.length > 120 ? `${line.slice(0, 117)}…` : line || "Working…";
  }, [message.content]);

  return (
    <details
      open={open}
      onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}
      className="mb-2 rounded-lg border border-zinc-200 bg-zinc-50/90 text-sm text-zinc-800 dark:border-zinc-700 dark:bg-zinc-900/60 dark:text-zinc-200"
    >
      <summary className="cursor-pointer select-none list-none px-3 py-2 font-medium [&::-webkit-details-marker]:hidden">
        <span className="inline-flex items-center gap-2">
          <span className="text-zinc-500 dark:text-zinc-400">
            {inProgress ? "Thinking" : "Trace"}
          </span>
          <span className="font-normal text-zinc-600 dark:text-zinc-300">{preview}</span>
          {inProgress ? (
            <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
          ) : null}
        </span>
      </summary>
      <div className="border-t border-zinc-200 px-3 py-2 dark:border-zinc-700">
        <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-words font-mono text-xs leading-relaxed text-zinc-700 dark:text-zinc-300">
          {message.content || "—"}
        </pre>
        <p className="mt-2 text-xs text-zinc-500 dark:text-zinc-500">
          Server-side workflow (knowledge search, SQL). Full results appear in the assistant reply and report widget.
        </p>
      </div>
    </details>
  );
}
