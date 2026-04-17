"use client";
import { useApp } from "@/providers/AppContext";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { PlusIcon, FileTextIcon, Loader2, LayoutGrid, Trash2 } from "lucide-react";
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
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const refreshHistory = useCallback(async () => {
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
  }, []);

  useEffect(() => {
    void refreshHistory();
  }, [activeThreadId, refreshHistory]);

  const onDeleteSession = useCallback(
    async (e: React.MouseEvent<HTMLButtonElement>, threadId: string) => {
      e.preventDefault();
      e.stopPropagation();
      if (deletingId) return;
      if (!window.confirm("Delete this conversation? This cannot be undone.")) return;
      setDeletingId(threadId);
      try {
        await api.deleteSession(threadId);
        setThreads((prev) => prev.filter((t) => t.id !== threadId));
        if (activeThreadId === threadId) {
          startNewConversation();
        }
      } catch {
        setError("Failed to delete conversation.");
      } finally {
        setDeletingId(null);
      }
    },
    [activeThreadId, deletingId, startNewConversation],
  );

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
            <div
              key={t.id}
              className={`flex w-full items-center gap-1 rounded-lg text-sm transition-all ${
                activeThreadId === t.id
                  ? "bg-zinc-800 text-white shadow-inner ring-1 ring-zinc-700"
                  : "hover:bg-zinc-800/50 hover:text-zinc-100"
              }`}
            >
              <button
                type="button"
                onClick={() => {
                  setPickedAgentId(AGENT_ORCHESTRATOR_ID);
                  setOrchestratorMainAgentId(DEFAULT_AGENT_ID);
                  setActiveThreadId(t.id);
                }}
                className="flex min-w-0 flex-1 items-center gap-3 p-3 text-left"
              >
                <FileTextIcon
                  size={16}
                  className={activeThreadId === t.id ? "text-blue-400" : "text-zinc-500"}
                />
                <span className="truncate">{t.name}</span>
              </button>
              <button
                type="button"
                title="Delete conversation"
                disabled={deletingId === t.id}
                onClick={(e) => void onDeleteSession(e, t.id)}
                className="shrink-0 rounded-md p-2 text-zinc-500 opacity-60 transition hover:bg-red-950/50 hover:text-red-400 hover:opacity-100 disabled:opacity-40"
                aria-label={`Delete ${t.name}`}
              >
                {deletingId === t.id ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Trash2 size={16} />
                )}
              </button>
            </div>
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
