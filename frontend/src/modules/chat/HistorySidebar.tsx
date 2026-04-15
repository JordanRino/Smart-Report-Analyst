"use client";
import { useApp } from "@/providers/AppContext";
import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { PlusIcon, FileTextIcon, Loader2, LayoutGrid } from "lucide-react";
import { api, ChatSession } from "@/lib/api";
import { AGENT_ORCHESTRATOR_ID, DEFAULT_AGENT_ID } from "@/lib/agents";

export function HistorySidebar() {
  const pathname = usePathname();
  const {
    activeThreadId,
    setActiveThreadId,
    startNewConversation,
    setPickedAgentId,
    setOrchestratorMainAgentId,
  } = useApp();
  const [threads, setThreads] = useState<ChatSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await api.getHistory();
        setThreads(data);
      } catch {
        setError("Failed to load history.");
      } finally {
        setLoading(false);
      }
    };
    void fetchHistory();
  }, [activeThreadId]);

  return (
    <div className="flex h-screen w-72 flex-col border-r border-zinc-800 bg-zinc-900 text-zinc-300">
      <div className="border-b border-zinc-800 p-4">
        <button
          onClick={() => startNewConversation()}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-zinc-100 py-2 font-medium text-zinc-900 transition hover:bg-white"
        >
          <PlusIcon size={16} /> New Chat
        </button>
      </div>

      <div className="min-h-0 flex-1 space-y-1 overflow-y-auto p-4">
        <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-zinc-500">
          Past conversations
        </h3>

        {loading ? (
          <div className="flex justify-center p-4">
            <Loader2 className="animate-spin text-zinc-500" />
          </div>
        ) : error ? (
          <p className="py-4 text-center text-xs text-red-400">{error}</p>
        ) : threads.length === 0 ? (
          <p className="py-4 text-center text-xs italic text-zinc-600">No past conversations yet.</p>
        ) : (
          threads.map((t) => (
            <button
              key={t.id}
              onClick={() => {
                setPickedAgentId(AGENT_ORCHESTRATOR_ID);
                setOrchestratorMainAgentId(DEFAULT_AGENT_ID);
                setActiveThreadId(t.id);
              }}
              className={`flex w-full items-center gap-3 rounded-lg p-3 text-sm transition-all ${
                activeThreadId === t.id
                  ? "bg-zinc-800 text-white shadow-inner ring-1 ring-zinc-700"
                  : "hover:bg-zinc-800/50 hover:text-zinc-100"
              }`}
            >
              <FileTextIcon
                size={16}
                className={activeThreadId === t.id ? "text-blue-400" : "text-zinc-500"}
              />
              <span className="truncate">{t.name}</span>
            </button>
          ))
        )}
      </div>

      <div className="mt-auto space-y-1 border-t border-zinc-800 p-3">
        <Link
          href="/"
          className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition ${
            pathname === "/"
              ? "bg-zinc-800 text-white"
              : "text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-100"
          }`}
        >
          <FileTextIcon size={16} />
          Chat
        </Link>
        <Link
          href="/reports"
          className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition ${
            pathname === "/reports"
              ? "bg-zinc-800 text-white"
              : "text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-100"
          }`}
        >
          <LayoutGrid size={16} />
          Reports
        </Link>
      </div>
    </div>
  );
}
