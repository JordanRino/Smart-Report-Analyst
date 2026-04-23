"use client";

import { useApp } from "@/providers/AppContext";
import { getApiPrefix } from "@/lib/env";
import { MAX_DRAFT_ROWS, writeDraft } from "@/modules/records/recordsDraftStorage";
import { useRouter } from "next/navigation";
import { Download, LayoutGrid, Save, Table2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";

type Props = {
  status: string;
  query: string;
  results: unknown;
  refinedUserQuestion?: string;
  rowCount?: number;
  /** ``execute_sql`` vs ``execute_metadata_sql`` card label */
  variant?: "analysis" | "metadata";
};

/** Stable fingerprint to avoid duplicate saves across re-renders. */
function resultsFingerprint(rows: unknown[]): string {
  if (rows.length === 0) return "0";
  try {
    const first = JSON.stringify(rows[0]);
    const last = rows.length > 1 ? JSON.stringify(rows[rows.length - 1]) : "";
    return `${rows.length}:${first}:${last}`;
  } catch {
    return `${rows.length}:err`;
  }
}

function rowsToCsv(rows: Record<string, unknown>[]): string {
  if (rows.length === 0) return "";
  const keys = Object.keys(rows[0]);
  const escape = (v: unknown) => {
    const s = v == null ? "" : String(v);
    return s.includes(",") || s.includes('"') || s.includes("\n")
      ? `"${s.replace(/"/g, '""')}"`
      : s;
  };
  const header = keys.map(escape).join(",");
  const body = rows.map((r) => keys.map((k) => escape(r[k])).join(",")).join("\n");
  return `${header}\n${body}`;
}

function downloadCsv(rows: Record<string, unknown>[], filename: string) {
  const csv = rowsToCsv(rows);
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/** CopilotKit ``execute_sql`` action renderer: shows SQL results as a Records card. */
export function SqlResultPdfReport({
  status,
  query,
  results,
  refinedUserQuestion,
  rowCount,
  variant = "analysis",
}: Props) {
  const router = useRouter();
  const { effectiveThreadId, pickedAgentId, orchestratorMainAgentId } = useApp();

  const rows = useMemo(
    () => (Array.isArray(results) ? (results as Record<string, unknown>[]) : []),
    [results],
  );
  const columns = useMemo(
    () => (rows.length > 0 ? Object.keys(rows[0]) : []),
    [rows],
  );

  const fingerprint = resultsFingerprint(rows);
  const saveKey = useMemo(
    () => `${variant}\0${query}\0${fingerprint}\0${refinedUserQuestion ?? ""}`,
    [variant, query, fingerprint, refinedUserQuestion],
  );

  const [previewOpen, setPreviewOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [savedMeta, setSavedMeta] = useState<{ id: string } | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const savedKeyRef = useRef<string | null>(null);

  // Reset save state when the result changes.
  useEffect(() => {
    setSavedMeta(null);
    setSaveError(null);
    savedKeyRef.current = null;
  }, [saveKey]);

  useEffect(() => {
    if (!previewOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setPreviewOpen(false);
    };
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [previewOpen]);

  const handleSave = useCallback(async () => {
    if (saving || savedMeta || savedKeyRef.current === saveKey) return;
    setSaving(true);
    setSaveError(null);
    try {
      const res = await fetch(`${getApiPrefix()}/records/saved`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          results: rows,
          executed_sql: query,
          refined_user_question: refinedUserQuestion || undefined,
          row_count: rowCount,
          thread_id: effectiveThreadId,
          agent_id: pickedAgentId,
          ...(pickedAgentId === "sra_orchestrator_agent" && orchestratorMainAgentId
            ? { main_agent_id: orchestratorMainAgentId }
            : {}),
        }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({})) as { detail?: string };
        setSaveError(typeof j.detail === "string" ? j.detail : `Save failed (${res.status})`);
        return;
      }
      const data = await res.json() as { id: string };
      savedKeyRef.current = saveKey;
      setSavedMeta(data);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Network error");
    } finally {
      setSaving(false);
    }
  }, [saving, savedMeta, saveKey, rows, query, refinedUserQuestion, rowCount,
      effectiveThreadId, pickedAgentId, orchestratorMainAgentId]);

  const openInRecords = useCallback(() => {
    writeDraft({
      version: 1,
      baseSql: query,
      rows: rows.slice(0, MAX_DRAFT_ROWS),
      refinedUserQuestion: refinedUserQuestion ?? null,
      rowCount: rowCount ?? null,
      filters: [],
    });
    router.push("/records/explore");
  }, [router, rows, query, refinedUserQuestion, rowCount]);

  const fileSlug = (refinedUserQuestion || (variant === "metadata" ? "metadata" : "records"))
    .replace(/[^a-zA-Z0-9_-]+/g, "-")
    .slice(0, 48) || (variant === "metadata" ? "metadata" : "records");

  const cardLabel = variant === "metadata" ? "Session metadata" : "Records";

  if (status === "inProgress") {
    return (
      <div className="my-4 rounded-lg border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm text-zinc-600">
        Running SQL…
      </div>
    );
  }
  if (status !== "complete") return null;

  const preview = rows.slice(0, 100);

  const overlay =
    previewOpen &&
    typeof document !== "undefined" &&
    createPortal(
      <div
        className="fixed inset-0 z-200 flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        aria-label={`${cardLabel} preview`}
      >
        <button
          type="button"
          className="absolute inset-0 bg-zinc-950/70 backdrop-blur-[1px]"
          aria-label="Close preview"
          onClick={() => setPreviewOpen(false)}
        />
        <div className="relative z-10 flex h-[min(88vh,900px)] w-full max-w-5xl flex-col overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-2xl">
          <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-zinc-100 bg-zinc-50 px-4 py-3">
            <span className="text-sm font-medium text-zinc-800">
              {cardLabel} preview{rows.length > 100 ? ` (first 100 of ${rows.length})` : ""}
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                className="inline-flex items-center gap-1 rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-xs font-semibold text-zinc-800 hover:bg-zinc-100"
                onClick={() => downloadCsv(rows, `${fileSlug}.csv`)}
              >
                <Download size={13} aria-hidden /> Download CSV
              </button>
              <button
                type="button"
                className="rounded-md bg-zinc-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-zinc-800"
                onClick={() => setPreviewOpen(false)}
              >
                Close
              </button>
            </div>
          </div>
          <div className="min-h-0 flex-1 overflow-auto bg-white">
            {columns.length > 0 ? (
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-zinc-100">
                  <tr>
                    {columns.map((col) => (
                      <th
                        key={col}
                        className="border-b border-zinc-200 px-3 py-2 text-left font-semibold text-zinc-700"
                      >
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.map((row, i) => (
                    <tr key={i} className={i % 2 === 0 ? "bg-white" : "bg-zinc-50"}>
                      {columns.map((col) => (
                        <td key={col} className="border-b border-zinc-100 px-3 py-1.5 text-zinc-800">
                          {String(row[col] ?? "")}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="p-6 text-sm text-zinc-500">No data returned.</p>
            )}
          </div>
        </div>
      </div>,
      document.body,
    );

  return (
    <>
      <div className="my-4 overflow-hidden rounded-lg border border-zinc-200 bg-white shadow-sm">
        <div className="flex flex-col gap-2 border-b border-zinc-100 bg-zinc-50 px-4 py-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-sm font-medium text-zinc-800">
              {cardLabel}
              {rows.length > 0 && (
                <span className="ml-1.5 text-xs font-normal text-zinc-500">
                  {rows.length} row{rows.length !== 1 ? "s" : ""}
                </span>
              )}
            </span>
            <button
              type="button"
              className="inline-flex items-center gap-1 rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-xs font-semibold text-zinc-800 hover:bg-zinc-100"
              onClick={() => setPreviewOpen(true)}
            >
              <Table2 size={13} aria-hidden /> Preview
            </button>
            <button
              type="button"
              disabled={rows.length === 0}
              className="inline-flex items-center gap-1 rounded-md border border-indigo-300 bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-950 hover:bg-indigo-100 disabled:opacity-60"
              onClick={openInRecords}
              title={`Opens the records workspace with up to ${MAX_DRAFT_ROWS} rows in this session`}
            >
              <LayoutGrid size={13} aria-hidden /> Open in records
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-1 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700"
              onClick={() => downloadCsv(rows, `${fileSlug}.csv`)}
            >
              <Download size={13} aria-hidden /> Download CSV
            </button>
            {savedMeta ? (
              <button
                type="button"
                disabled
                className="inline-flex items-center gap-1 rounded-md border border-green-400 bg-green-50 px-3 py-1.5 text-xs font-semibold text-green-800"
              >
                <Save size={13} aria-hidden /> Saved!
              </button>
            ) : (
              <button
                type="button"
                disabled={saving || rows.length === 0}
                className="inline-flex items-center gap-1 rounded-md border border-amber-300 bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-950 hover:bg-amber-100 disabled:opacity-60"
                onClick={() => void handleSave()}
              >
                <Save size={13} aria-hidden /> {saving ? "Saving…" : "Save"}
              </button>
            )}
          </div>
          {saveError && (
            <p className="text-xs text-red-700">{saveError}</p>
          )}
        </div>
        {/* Inline mini-table (first 5 rows) */}
        {columns.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-zinc-50">
                  {columns.map((col) => (
                    <th
                      key={col}
                      className="border-b border-zinc-200 px-3 py-2 text-left font-semibold text-zinc-600"
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.slice(0, 5).map((row, i) => (
                  <tr key={i} className={i % 2 === 0 ? "bg-white" : "bg-zinc-50"}>
                    {columns.map((col) => (
                      <td
                        key={col}
                        className="border-b border-zinc-100 px-3 py-1.5 text-zinc-800"
                      >
                        {String(row[col] ?? "")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {rows.length > 5 && (
              <p className="border-t border-zinc-100 px-3 py-2 text-[11px] text-zinc-400">
                {rows.length - 5} more row{rows.length - 5 !== 1 ? "s" : ""} — use Preview or Download CSV to see all.
              </p>
            )}
          </div>
        )}
      </div>
      {overlay}
    </>
  );
}
