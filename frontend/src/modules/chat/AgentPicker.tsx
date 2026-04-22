"use client";

import { useApp } from "@/providers/AppContext";
import { MAIN_SPECIALIST_OPTIONS, type AgentId } from "@/lib/agents";
import { api } from "@/lib/api";
import { useCallback, useEffect, useId, useRef, useState } from "react";

/**
 * Session-only shell: Copilot agent is always the orchestrator; user picks the main agent
 * (``mainAgentId``). Single compact custom menu.
 */
export function AgentPicker() {
  const { orchestratorMainAgentId, setOrchestratorMainAgentId, effectiveThreadId } = useApp();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const listId = useId();

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  const selected = MAIN_SPECIALIST_OPTIONS.find((a) => a.id === orchestratorMainAgentId);
  const triggerLabel = selected?.shortLabel ?? "Choose…";

  const onPick = useCallback(
    (id: AgentId) => {
      setOrchestratorMainAgentId(id);
      setOpen(false);
      // Persist to backend — fire-and-forget. React state drives the UI immediately;
      // the API call ensures the backend knows the specialist for this thread.
      void api.setSpecialist(effectiveThreadId, id).catch(() => {
        // Non-fatal: the backend will fall back to the "choose a specialist" prompt
        // if state is missing, which is the correct degradation path.
      });
    },
    [setOrchestratorMainAgentId, effectiveThreadId],
  );

  return (
    <div className="border-b border-white/8 bg-[#0a0a0a] px-4 py-2">
      <div className="mx-auto flex max-w-5xl items-center justify-end gap-3">
        <span className="shrink-0 text-[10px] font-medium tracking-[0.22em] text-neutral-500 uppercase">
          Team specialist
        </span>
        <div ref={rootRef} className="relative w-[min(100%,200px)]">
          <button
            type="button"
            aria-expanded={open}
            aria-controls={listId}
            aria-haspopup="listbox"
            onClick={() => setOpen((o) => !o)}
            className="flex h-9 w-full items-center justify-between gap-2 rounded-lg border border-white/10 bg-[#101010] px-2.5 text-left text-[12px] font-semibold tracking-wide text-neutral-100 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] outline-none transition hover:border-[#c9a227]/45 focus-visible:ring-2 focus-visible:ring-[#c9a227]/45"
          >
            <span className={selected ? "text-neutral-100" : "text-neutral-500"}>{triggerLabel}</span>
            <span className="text-[10px] text-neutral-500" aria-hidden>
              ▾
            </span>
          </button>
          {open ? (
            <ul
              id={listId}
              role="listbox"
              className="absolute top-[calc(100%+5px)] right-0 z-50 w-full overflow-hidden rounded-lg border border-white/10 bg-[#0c0c0c] py-0.5 shadow-[0_12px_40px_-8px_rgba(0,0,0,0.9),0_0_0_1px_rgba(201,162,39,0.12)]"
            >
              {MAIN_SPECIALIST_OPTIONS.map((a) => (
                <li key={a.id} className="px-0.5">
                  <button
                    type="button"
                    role="option"
                    aria-selected={orchestratorMainAgentId === a.id}
                    className={`flex w-full cursor-pointer rounded-md px-2.5 py-2 text-left text-[11px] font-medium leading-snug transition ${
                      orchestratorMainAgentId === a.id
                        ? "bg-[#c9a227]/14 text-[#ebe2bc]"
                        : "text-neutral-300 hover:bg-white/6 hover:text-neutral-50"
                    }`}
                    onClick={() => onPick(a.id)}
                  >
                    {a.shortLabel}
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
        {orchestratorMainAgentId ? (
          <button
            type="button"
            className="shrink-0 rounded-md px-1.5 py-1 text-[10px] font-medium tracking-wide text-neutral-500 transition hover:bg-white/5 hover:text-[#c9a227]"
            onClick={() => {
              setOrchestratorMainAgentId(null);
              void api.setSpecialist(effectiveThreadId, null).catch(() => {});
            }}
            title="Clear specialist"
          >
            Reset
          </button>
        ) : null}
      </div>
    </div>
  );
}
