"use client";

import { HistorySidebar } from "@/modules/chat/HistorySidebar";
import { api, type ReportSummary } from "@/lib/api";
import { getAgentLabel } from "@/lib/agents";
import { getApiPrefix } from "@/lib/env";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { Loader2, Trash2, ExternalLink, Eye, Download } from "lucide-react";

function openChatHrefFromReport(row: ReportSummary): string {
  const qs = new URLSearchParams();
  qs.set("thread", row.thread_id);
  qs.set("agent", row.agent_id);
  if (row.main_agent_id) qs.set("mainAgent", row.main_agent_id);
  return `/?${qs.toString()}`;
}

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

export default function ReportsDashboard() {
  const [items, setItems] = useState<ReportSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listReports("report");
      setItems(res.items);
      setTotal(res.total);
    } catch {
      setError("Could not load items.");
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // PDF preview uses a blob URL so the browser can embed the downloaded bytes in an <object>.
  useEffect(() => {
    if (!previewId) {
      setPreviewUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev);
        return null;
      });
      return;
    }
    setPreviewUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return null;
    });
    const ac = new AbortController();
    void (async () => {
      try {
        const res = await fetch(
          `${getApiPrefix()}/reports/saved/${encodeURIComponent(previewId)}/file`,
          { signal: ac.signal },
        );
        if (!res.ok) {
          if (!ac.signal.aborted) setPreviewUrl(null);
          return;
        }
        const blob = await res.blob();
        if (ac.signal.aborted) return;
        setPreviewUrl(URL.createObjectURL(blob));
      } catch {
        if (!ac.signal.aborted) setPreviewUrl(null);
      }
    })();
    return () => ac.abort();
  }, [previewId]);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  useEffect(() => {
    if (previewId === null) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setPreviewId(null);
    };
    window.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [previewId]);

  async function handleDelete(id: string) {
    if (!window.confirm("Remove this item from the dashboard?")) return;
    setDeletingId(id);
    try {
      await api.deleteReport(id);
      setPreviewId((p) => (p === id ? null : p));
      await load();
    } catch {
      setError("Delete failed.");
    } finally {
      setDeletingId(null);
    }
  }

  const overlay =
    previewId !== null &&
    typeof document !== "undefined" &&
    createPortal(
      <div
        className="fixed inset-0 z-200 flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        aria-label="PDF preview"
      >
        <button
          type="button"
          className="absolute inset-0 bg-zinc-950/70 backdrop-blur-[1px]"
          aria-label="Close preview"
          onClick={() => setPreviewId(null)}
        />
        <div className="relative z-10 flex h-[min(88vh,900px)] w-full max-w-5xl flex-col overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-2xl">
          <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-zinc-100 bg-zinc-50 px-4 py-3">
            <span className="text-sm font-medium text-zinc-800">Report preview</span>
            <button
              type="button"
              className="rounded-md bg-zinc-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-zinc-800"
              onClick={() => setPreviewId(null)}
            >
              Close
            </button>
          </div>
          <div className="min-h-0 flex-1 bg-zinc-100">
            {previewUrl ? (
              <object
                data={previewUrl}
                type="application/pdf"
                className="h-full w-full min-h-[400px]"
                title="Report preview"
              >
                <p className="p-4 text-sm text-zinc-600">Preview not available. Download from the list.</p>
              </object>
            ) : (
              <div className="flex h-64 items-center justify-center text-sm text-zinc-500">
                <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading…
              </div>
            )}
          </div>
        </div>
      </div>,
      document.body,
    );

  return (
    <div className="flex h-screen w-full overflow-hidden bg-zinc-50">
      <HistorySidebar />
      <main className="flex min-h-0 min-w-0 flex-1 flex-col bg-white">
        <header className="flex h-16 shrink-0 items-center justify-between border-b px-8">
          <h1 className="text-sm font-bold uppercase tracking-widest text-zinc-900">Reports</h1>
          <span className="text-xs text-zinc-500">{total} saved</span>
        </header>

        <div className="min-h-0 flex-1 overflow-auto p-8">
          {loading ? (
            <div className="flex justify-center py-16 text-zinc-500">
              <Loader2 className="h-8 w-8 animate-spin" />
            </div>
          ) : error ? (
            <p className="text-sm text-red-600">{error}</p>
          ) : items.length === 0 ? (
            <p className="text-sm text-zinc-500">
              No saved reports yet. Ask the orchestrator to build a report, then save it.
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
                      {formatWhen(row.created_at)} · {getAgentLabel(row.agent_id)} · thread{" "}
                      <code className="rounded bg-zinc-100 px-1 text-[11px]">
                        {row.thread_id.slice(0, 8)}…
                      </code>
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      className="inline-flex items-center gap-1 rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-xs font-semibold text-zinc-800 hover:bg-zinc-50"
                      onClick={() => setPreviewId(row.id)}
                    >
                      <Eye size={14} /> Preview
                    </button>
                    <a
                      href={`${getApiPrefix()}/reports/saved/${encodeURIComponent(row.id)}/file`}
                      download={`${row.title.replace(/[^a-zA-Z0-9_-]+/g, "-").slice(0, 48) || "report"}.pdf`}
                      className="inline-flex items-center gap-1 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700"
                    >
                      <Download size={14} /> Download PDF
                    </a>
                    <Link
                      href={openChatHrefFromReport(row)}
                      className="inline-flex items-center gap-1 rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-xs font-semibold text-zinc-800 hover:bg-zinc-50"
                    >
                      <ExternalLink size={14} /> Open chat
                    </Link>
                    <button
                      type="button"
                      disabled={deletingId === row.id}
                      className="inline-flex items-center gap-1 rounded-md border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-semibold text-red-800 hover:bg-red-100 disabled:opacity-50"
                      onClick={() => void handleDelete(row.id)}
                    >
                      <Trash2 size={14} /> {deletingId === row.id ? "…" : "Delete"}
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>
      {overlay}
    </div>
  );
}
