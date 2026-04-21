"use client";

import { HistorySidebar } from "@/modules/chat/HistorySidebar";
import { api, type ReportSummary } from "@/lib/api";
import { getAgentLabel } from "@/lib/agents";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ExternalLink, LayoutGrid, Loader2, Pencil, Trash2 } from "lucide-react";

function formatWhen(ms: number): string {
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(ms));
  } catch {
    return String(ms);
  }
}

export default function RecordsList() {
  const router = useRouter();
  const [items, setItems] = useState<ReportSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listReports("record");
      setItems(res.items);
      setTotal(res.total);
    } catch {
      setError("Could not load saved records.");
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleDelete(id: string) {
    if (!window.confirm("Delete this saved record from the library?")) return;
    setDeletingId(id);
    try {
      await api.deleteReport(id);
      await load();
    } catch {
      setError("Delete failed.");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="flex h-screen w-full overflow-hidden bg-zinc-50">
      <HistorySidebar />
      <main className="flex min-h-0 min-w-0 flex-1 flex-col bg-white">
        <header className="flex h-16 shrink-0 items-center justify-between border-b px-8">
          <div className="flex items-center gap-3">
            <LayoutGrid className="h-4 w-4 text-blue-600" aria-hidden />
            <h1 className="text-sm font-bold uppercase tracking-widest text-zinc-900">Records library</h1>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-zinc-500">{total} saved</span>
            <Link
              href="/records/explore"
              className="rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-xs font-semibold text-zinc-800 hover:bg-zinc-50"
            >
              Workspace
            </Link>
          </div>
        </header>

        <div className="min-h-0 flex-1 overflow-auto p-8">
          {loading ? (
            <div className="flex justify-center py-16 text-zinc-500">
              <Loader2 className="h-8 w-8 animate-spin" aria-hidden />
            </div>
          ) : error ? (
            <p className="text-sm text-red-600">{error}</p>
          ) : items.length === 0 ? (
            <p className="text-sm text-zinc-500">
              No saved records yet. Save from the records workspace or from chat.
            </p>
          ) : (
            <ul className="space-y-3">
              {items.map((row) => (
                <li
                  key={row.id}
                  className="flex flex-col gap-3 rounded-lg border border-zinc-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium text-zinc-900">{row.title}</p>
                    <p className="mt-1 text-xs text-zinc-500">
                      {formatWhen(row.created_at)} · {getAgentLabel(row.agent_id)} ·{" "}
                      {row.results_row_count} rows
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      onClick={() => router.push(`/records/explore?saved=${encodeURIComponent(row.id)}`)}
                      className="inline-flex items-center gap-1 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700"
                    >
                      <Pencil size={14} aria-hidden /> Open in workspace
                    </button>
                    <Link
                      href={`/?thread=${encodeURIComponent(row.thread_id)}&agent=${encodeURIComponent(row.agent_id)}${row.main_agent_id ? `&mainAgent=${encodeURIComponent(row.main_agent_id)}` : ""}`}
                      className="inline-flex items-center gap-1 rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-xs font-semibold text-zinc-800 hover:bg-zinc-50"
                    >
                      <ExternalLink size={14} aria-hidden /> Open chat
                    </Link>
                    <button
                      type="button"
                      disabled={deletingId === row.id}
                      className="inline-flex items-center gap-1 rounded-md border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-semibold text-red-800 hover:bg-red-100 disabled:opacity-50"
                      onClick={() => void handleDelete(row.id)}
                    >
                      <Trash2 size={14} aria-hidden /> {deletingId === row.id ? "…" : "Delete"}
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>
    </div>
  );
}
