"use client";

import { HistorySidebar } from "@/modules/chat/HistorySidebar";
import { api, type ReportSummary } from "@/lib/api";
import { getAgentLabel } from "@/lib/agents";
import { getApiPrefix } from "@/lib/env";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { Loader2, Trash2, ExternalLink, Eye, Download } from "lucide-react";

type KindFilter = "all" | "record" | "report";

function parseCsvToRows(csv: string): { columns: string[]; rows: string[][] } {
  const lines = csv.trim().split("\n");
  if (lines.length === 0) return { columns: [], rows: [] };
  const splitLine = (line: string) => {
    const result: string[] = [];
    let cur = "";
    let inQuote = false;
    for (let i = 0; i < line.length; i++) {
      const ch = line[i];
      if (ch === '"') {
        if (inQuote && line[i + 1] === '"') { cur += '"'; i++; }
        else inQuote = !inQuote;
      } else if (ch === "," && !inQuote) {
        result.push(cur); cur = "";
      } else {
        cur += ch;
      }
    }
    result.push(cur);
    return result;
  };
  const columns = splitLine(lines[0]);
  const rows = lines.slice(1).map(splitLine);
  return { columns, rows };
}

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

const FILTER_TABS: { label: string; value: KindFilter }[] = [
  { label: "All", value: "all" },
  { label: "Reports", value: "report" },
  { label: "Records", value: "record" },
];

export default function ReportsDashboard() {
  const [kindFilter, setKindFilter] = useState<KindFilter>("all");
  const [items, setItems] = useState<ReportSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [recordPreviewId, setRecordPreviewId] = useState<string | null>(null);
  const [recordPreviewData, setRecordPreviewData] = useState<{ columns: string[]; rows: string[][] } | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const load = useCallback(
    async (kind: KindFilter) => {
      setLoading(true);
      setError(null);
      try {
        const res = await api.listReports(kind === "all" ? undefined : kind);
        setItems(res.items);
        setTotal(res.total);
      } catch {
        setError("Could not load items.");
        setItems([]);
        setTotal(0);
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    void load(kindFilter);
  }, [load, kindFilter]);

  // PDF preview blob URL
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

  // Fetch and parse CSV for records preview
  useEffect(() => {
    if (!recordPreviewId) { setRecordPreviewData(null); return; }
    const ac = new AbortController();
    void (async () => {
      try {
        const res = await fetch(
          `${getApiPrefix()}/records/saved/${encodeURIComponent(recordPreviewId)}/file`,
          { signal: ac.signal },
        );
        if (!res.ok || ac.signal.aborted) return;
        const text = await res.text();
        if (ac.signal.aborted) return;
        setRecordPreviewData(parseCsvToRows(text));
      } catch { /* non-fatal */ }
    })();
    return () => ac.abort();
  }, [recordPreviewId]);

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
      await load(kindFilter);
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

  const recordOverlay =
    recordPreviewId !== null &&
    typeof document !== "undefined" &&
    createPortal(
      <div
        className="fixed inset-0 z-200 flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        aria-label="Records preview"
      >
        <button
          type="button"
          className="absolute inset-0 bg-zinc-950/70 backdrop-blur-[1px]"
          aria-label="Close preview"
          onClick={() => setRecordPreviewId(null)}
        />
        <div className="relative z-10 flex h-[min(88vh,900px)] w-full max-w-5xl flex-col overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-2xl">
          <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-zinc-100 bg-zinc-50 px-4 py-3">
            <span className="text-sm font-medium text-zinc-800">Records preview</span>
            <div className="flex gap-2">
              <a
                href={`${getApiPrefix()}/records/saved/${encodeURIComponent(recordPreviewId)}/file`}
                download="records.csv"
                className="rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-xs font-semibold text-zinc-800 hover:bg-zinc-100"
              >
                Download CSV
              </a>
              <button
                type="button"
                className="rounded-md bg-zinc-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-zinc-800"
                onClick={() => setRecordPreviewId(null)}
              >
                Close
              </button>
            </div>
          </div>
          <div className="min-h-0 flex-1 overflow-auto bg-white">
            {recordPreviewData && recordPreviewData.columns.length > 0 ? (
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-zinc-100">
                  <tr>
                    {recordPreviewData.columns.map((col) => (
                      <th key={col} className="border-b border-zinc-200 px-3 py-2 text-left font-semibold text-zinc-700">
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {recordPreviewData.rows.map((row, i) => (
                    <tr key={i} className={i % 2 === 0 ? "bg-white" : "bg-zinc-50"}>
                      {row.map((cell, j) => (
                        <td key={j} className="border-b border-zinc-100 px-3 py-1.5 text-zinc-800">
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="flex h-32 items-center justify-center text-sm text-zinc-500">
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
          <h1 className="text-sm font-bold uppercase tracking-widest text-zinc-900">
            Reports &amp; Records
          </h1>
          <span className="text-xs text-zinc-500">{total} total</span>
        </header>

        {/* Filter tabs */}
        <div className="flex shrink-0 gap-1 border-b border-zinc-100 px-8 pt-3 pb-0">
          {FILTER_TABS.map((tab) => (
            <button
              key={tab.value}
              type="button"
              onClick={() => setKindFilter(tab.value)}
              className={`rounded-t-md px-4 py-2 text-xs font-semibold transition ${
                kindFilter === tab.value
                  ? "border border-b-white border-zinc-200 bg-white text-zinc-900"
                  : "text-zinc-500 hover:text-zinc-800"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="min-h-0 flex-1 overflow-auto p-8">
          {loading ? (
            <div className="flex justify-center py-16 text-zinc-500">
              <Loader2 className="h-8 w-8 animate-spin" />
            </div>
          ) : error ? (
            <p className="text-sm text-red-600">{error}</p>
          ) : items.length === 0 ? (
            <p className="text-sm text-zinc-500">
              {kindFilter === "record"
                ? "No saved records yet. Run a SQL query in chat and click Save."
                : kindFilter === "report"
                  ? "No saved reports yet. Ask the orchestrator to build a report, then save it."
                  : "No saved items yet."}
            </p>
          ) : (
            <ul className="space-y-3">
              {items.map((row) => {
                const isRecord = row.kind === "record";
                return (
                  <li
                    key={row.id}
                    className="flex flex-col gap-3 rounded-lg border border-zinc-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span
                          className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                            isRecord
                              ? "bg-blue-50 text-blue-700"
                              : "bg-indigo-50 text-indigo-700"
                          }`}
                        >
                          {isRecord ? "Record" : "Report"}
                        </span>
                        <p className="truncate font-medium text-zinc-900">{row.title}</p>
                      </div>
                      <p className="mt-1 text-xs text-zinc-500">
                        {formatWhen(row.created_at)} · {getAgentLabel(row.agent_id)} · thread{" "}
                        <code className="rounded bg-zinc-100 px-1 text-[11px]">
                          {row.thread_id.slice(0, 8)}…
                        </code>
                        {isRecord && row.results_row_count != null && (
                          <> · {row.results_row_count} rows</>
                        )}
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      {isRecord ? (
                        <>
                          <button
                            type="button"
                            className="inline-flex items-center gap-1 rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-xs font-semibold text-zinc-800 hover:bg-zinc-50"
                            onClick={() => setRecordPreviewId(row.id)}
                          >
                            <Eye size={14} /> Preview
                          </button>
                          <a
                            href={`${getApiPrefix()}/records/saved/${encodeURIComponent(row.id)}/file`}
                            download={`${row.title.replace(/[^a-zA-Z0-9_-]+/g, "-").slice(0, 48) || "records"}.csv`}
                            className="inline-flex items-center gap-1 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700"
                          >
                            <Download size={13} /> Download CSV
                          </a>
                        </>
                      ) : (
                        <>
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
                        </>
                      )}
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
                );
              })}
            </ul>
          )}
        </div>
      </main>
      {overlay}
      {recordOverlay}
    </div>
  );
}
