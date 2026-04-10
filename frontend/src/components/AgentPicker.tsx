"use client";

import { useApp } from "@/context/AppContext";
import { AGENTS, getAgentLabel, type AgentId } from "@/lib/agents";

export function AgentPicker() {
  const { pickedAgentId, setPickedAgentId, clearPickedAgent } = useApp();

  const isRouter = pickedAgentId === "sra_router_agent";

  if (isRouter) {
    return (
      <div className="flex flex-wrap items-center gap-2 border-b border-zinc-200 bg-zinc-50/95 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900/40">
        <span className="text-xs font-medium text-zinc-600 dark:text-zinc-400">Agent</span>
        <select
          id="sra-agent-picker"
          value={pickedAgentId}
          onChange={(e) => setPickedAgentId(e.target.value as AgentId)}
          className="max-w-[min(100%,280px)] rounded-md border border-zinc-300 bg-white px-2 py-1.5 text-xs text-zinc-900 shadow-sm dark:border-zinc-600 dark:bg-zinc-950 dark:text-zinc-100"
        >
          {AGENTS.map((a) => (
            <option key={a.id} value={a.id}>
              {a.label}
            </option>
          ))}
        </select>
        <span className="text-[11px] text-zinc-500 dark:text-zinc-500">
          Choose who answers; each agent keeps its own memory for this chat thread.
        </span>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-zinc-200 bg-zinc-50/95 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900/40">
      <span className="text-xs text-zinc-500 dark:text-zinc-400">Active agent</span>
      <span className="inline-flex items-center gap-1 rounded-full border border-blue-200 bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-900 dark:border-blue-900 dark:bg-blue-950/50 dark:text-blue-100">
        {getAgentLabel(pickedAgentId)}
        <button
          type="button"
          onClick={clearPickedAgent}
          className="ml-0.5 flex h-5 w-5 items-center justify-center rounded-full text-blue-800 hover:bg-blue-200/80 dark:text-blue-200 dark:hover:bg-blue-900/80"
          title="Clear agent — open picker"
          aria-label="Clear selected agent"
        >
          ×
        </button>
      </span>
    </div>
  );
}
