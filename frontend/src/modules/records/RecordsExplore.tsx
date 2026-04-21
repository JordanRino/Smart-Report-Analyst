"use client";

import { HistorySidebar } from "@/modules/chat/HistorySidebar";
import {
  applyOfflineFilters,
  buildComposedSqlDisplay,
  columnUnion,
} from "@/modules/records/recordsFilterEngine";
import type { RecordFilterRow } from "@/modules/records/recordsFilterTypes";
import { RECORD_FILTER_OPS } from "@/modules/records/recordsFilterTypes";
import {
  clearDraft,
  MAX_DRAFT_ROWS,
  readDraft,
  writeDraft,
  type RecordsDraftV1,
} from "@/modules/records/recordsDraftStorage";
import { buildDiscussPrefillText } from "@/modules/records/discussPrefill";
import { csvRowsToObjects, parseCsvToRows } from "@/modules/records/csvParse";
import { stashPendingChatPrefill } from "@/lib/chatPrefillStorage";
import { getApiPrefix } from "@/lib/env";
import type { ReportSummary } from "@/lib/api";
import { useApp } from "@/providers/AppContext";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { LayoutGrid, Loader2, MessageSquare, Plus, Save, Trash2 } from "lucide-react";

function newFilterId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function parseFiltersJson(raw: string | null | undefined): RecordFilterRow[] {
  if (!raw || !raw.trim()) return [];
  try {
    const arr = JSON.parse(raw) as unknown[];
    if (!Array.isArray(arr)) return [];
    return arr
      .map((x) => x as Record<string, unknown>)
      .filter((x) => typeof x?.column === "string" && typeof x?.op === "string")
      .map((x) => ({
        id: typeof x.id === "string" ? x.id : newFilterId(),
        column: String(x.column),
        op: x.op as RecordFilterRow["op"],
        value: typeof x.value === "string" ? x.value : "",
      }));
  } catch {
    return [];
  }
}

export default function RecordsExplore() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const savedIdParam = searchParams.get("saved")?.trim() ?? "";
  const { effectiveThreadId, pickedAgentId, orchestratorMainAgentId } = useApp();

  const [loadError, setLoadError] = useState<string | null>(null);
  const [loadingSaved, setLoadingSaved] = useState(false);

  const [baseSql, setBaseSql] = useState("");
  const [allRows, setAllRows] = useState<Record<string, unknown>[]>([]);
  const [refinedTitle, setRefinedTitle] = useState("");
  const [sourceSavedId, setSourceSavedId] = useState<string | null>(null);
  const [savedMeta, setSavedMeta] = useState<ReportSummary | null>(null);

  const [filters, setFilters] = useState<RecordFilterRow[]>([]);
  const [tab, setTab] = useState<"data" | "sql">("data");

  const [saveTitle, setSaveTitle] = useState("");
  const [saveModalOpen, setSaveModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveOkId, setSaveOkId] = useState<string | null>(null);

  const hydrateFromDraft = useCallback((d: RecordsDraftV1) => {
    setBaseSql(d.baseSql);
    setAllRows(d.rows);
    setRefinedTitle((d.refinedUserQuestion ?? "").trim() || "Untitled exploration");
    setSourceSavedId(d.sourceSavedId ?? null);
    setSavedMeta(null);
    setFilters(Array.isArray(d.filters) ? d.filters : []);
    setSaveTitle((d.refinedUserQuestion ?? "").trim() || "");
    setSaveOkId(null);
  }, []);

  useEffect(() => {
    if (savedIdParam) {
      setLoadingSaved(true);
      setLoadError(null);
      void (async () => {
        try {
          const meta = (await fetch(
            `${getApiPrefix()}/reports/saved/${encodeURIComponent(savedIdParam)}`,
          ).then((r) => {
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            return r.json();
          })) as ReportSummary & { filters_json?: string | null };
          if (meta.kind && meta.kind !== "record") {
            throw new Error("Not a saved record");
          }
          const csvText = await fetch(
            `${getApiPrefix()}/records/saved/${encodeURIComponent(savedIdParam)}/file`,
          ).then((r) => {
            if (!r.ok) throw new Error("Could not load CSV");
            return r.text();
          });
          const { columns, rows } = parseCsvToRows(csvText);
          const objs = csvRowsToObjects(columns, rows);
          setBaseSql(meta.executed_sql || "");
          setAllRows(objs);
          setRefinedTitle(meta.title || "Saved records");
          setSourceSavedId(savedIdParam);
          setSavedMeta(meta);
          setFilters(parseFiltersJson(meta.filters_json));
          setSaveTitle(meta.title || "");
          setSaveOkId(null);
        } catch (e) {
          setLoadError(e instanceof Error ? e.message : "Load failed");
        } finally {
          setLoadingSaved(false);
        }
      })();
      return;
    }

    const draft = readDraft();
    if (draft) {
      hydrateFromDraft(draft);
    } else {
      setLoadError(null);
      setBaseSql("");
      setAllRows([]);
      setRefinedTitle("Records exploration");
      setSourceSavedId(null);
      setSavedMeta(null);
      setFilters([]);
      setSaveTitle("");
      setSaveOkId(null);
    }
  }, [savedIdParam, hydrateFromDraft]);

  const columns = useMemo(() => columnUnion(allRows), [allRows]);

  const filteredRows = useMemo(
    () => applyOfflineFilters(allRows, filters),
    [allRows, filters],
  );

  const composedSql = useMemo(
    () => buildComposedSqlDisplay(baseSql, filters),
    [baseSql, filters],
  );

  const persistDraft = useCallback(() => {
    if (savedIdParam) return;
    if (allRows.length === 0) return;
    writeDraft({
      version: 1,
      baseSql,
      rows: allRows,
      refinedUserQuestion: refinedTitle,
      filters,
      sourceSavedId: sourceSavedId ?? undefined,
    });
  }, [savedIdParam, baseSql, allRows, refinedTitle, filters, sourceSavedId]);

  useEffect(() => {
    if (savedIdParam || allRows.length === 0) return;
    persistDraft();
  }, [savedIdParam, allRows, baseSql, filters, refinedTitle, persistDraft]);

  const addFilter = () => {
    setFilters((prev) => [
      ...prev,
      {
        id: newFilterId(),
        column: columns[0] ?? "",
        op: "eq",
        value: "",
      },
    ]);
  };

  const updateFilter = (id: string, patch: Partial<RecordFilterRow>) => {
    setFilters((prev) => prev.map((f) => (f.id === id ? { ...f, ...patch } : f)));
  };

  const removeFilter = (id: string) => {
    setFilters((prev) => prev.filter((f) => f.id !== id));
  };

  const clearExploration = () => {
    if (!window.confirm("Discard this exploration? Unsaved changes will be lost.")) return;
    clearDraft();
    router.push("/records");
  };

  const submitSave = async () => {
    if (allRows.length === 0) return;
    setSaving(true);
    setSaveError(null);
    try {
      const title = (saveTitle || refinedTitle || "Saved view").trim().slice(0, 500);
      const filtersJson = JSON.stringify(filters);
      const threadId = savedMeta?.thread_id ?? effectiveThreadId;
      const agentId = savedMeta?.agent_id ?? pickedAgentId;
      const mainAgentId =
        savedMeta?.main_agent_id ??
        (pickedAgentId === "sra_orchestrator_agent" ? orchestratorMainAgentId : null);

      const res = await fetch(`${getApiPrefix()}/records/saved`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          results: allRows,
          executed_sql: baseSql,
          refined_user_question: title,
          row_count: allRows.length,
          thread_id: threadId,
          agent_id: agentId,
          ...(mainAgentId ? { main_agent_id: mainAgentId } : {}),
          title,
          filters_json: filtersJson,
          composed_sql: composedSql,
        }),
      });
      if (!res.ok) {
        const j = (await res.json().catch(() => ({}))) as { detail?: string };
        setSaveError(typeof j.detail === "string" ? j.detail : `Save failed (${res.status})`);
        return;
      }
      const data = (await res.json()) as { id: string };
      setSaveOkId(data.id);
      clearDraft();
      setSaveModalOpen(false);
      router.replace(`/records/explore?saved=${encodeURIComponent(data.id)}`);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Network error");
    } finally {
      setSaving(false);
    }
  };

  const discussInChat = () => {
    const threadId = savedMeta?.thread_id ?? effectiveThreadId;
    const agentId = savedMeta?.agent_id ?? pickedAgentId;
    const mainAgentId =
      savedMeta?.main_agent_id ??
      (pickedAgentId === "sra_orchestrator_agent" ? orchestratorMainAgentId : undefined);

    const blob = buildDiscussPrefillText({
      title: refinedTitle || saveTitle || "Records",
      baseSql,
      filters,
      composedSql,
      filteredRowCount: filteredRows.length,
      totalRowCount: allRows.length,
      savedRecordId: sourceSavedId ?? saveOkId,
    });
    stashPendingChatPrefill(threadId, blob);
    const qs = new URLSearchParams();
    qs.set("thread", threadId);
    qs.set("agent", agentId);
    if (mainAgentId) qs.set("mainAgent", mainAgentId);
    router.push(`/?${qs.toString()}`);
  };

  const emptyNoDraft = !savedIdParam && allRows.length === 0 && !loadingSaved;

  return (
    <div className="flex h-screen w-full overflow-hidden bg-zinc-50">
      <HistorySidebar />
      <main className="flex min-h-0 min-w-0 flex-1 flex-col bg-white">
        <header className="flex h-16 shrink-0 flex-wrap items-center justify-between gap-2 border-b px-6">
          <div className="flex min-w-0 items-center gap-3">
            <LayoutGrid className="h-4 w-4 shrink-0 text-blue-600" aria-hidden />
            <h1 className="truncate text-sm font-bold uppercase tracking-widest text-zinc-900">
              Records workspace
            </h1>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Link
              href="/records"
              className="rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-xs font-semibold text-zinc-800 hover:bg-zinc-50"
            >
              Library
            </Link>
            <button
              type="button"
              disabled={allRows.length === 0}
              onClick={() => discussInChat()}
              className="inline-flex items-center gap-1 rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-xs font-semibold text-zinc-800 hover:bg-zinc-50 disabled:opacity-50"
            >
              <MessageSquare size={14} aria-hidden /> Discuss in chat
            </button>
            <button
              type="button"
              disabled={allRows.length === 0}
              onClick={() => {
                setSaveTitle((refinedTitle || saveTitle).trim());
                setSaveModalOpen(true);
              }}
              className="inline-flex items-center gap-1 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
            >
              <Save size={14} aria-hidden /> Save view
            </button>
            <button
              type="button"
              onClick={clearExploration}
              className="inline-flex items-center gap-1 rounded-md border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-semibold text-red-800 hover:bg-red-100"
            >
              <Trash2 size={14} aria-hidden /> Clear
            </button>
          </div>
        </header>

        {loadingSaved ? (
          <div className="flex flex-1 items-center justify-center text-zinc-500">
            <Loader2 className="h-8 w-8 animate-spin" aria-label="Loading" />
          </div>
        ) : emptyNoDraft ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center">
            <p className="max-w-md text-sm text-zinc-600">
              No exploration loaded. Run SQL in chat and choose <strong>Open in records</strong>, or open a
              saved record from the{" "}
              <Link href="/records" className="font-semibold text-blue-600 underline">
                records library
              </Link>
              .
            </p>
          </div>
        ) : (
          <>
            {loadError && (
              <div className="border-b border-red-200 bg-red-50 px-6 py-2 text-sm text-red-800">{loadError}</div>
            )}
            <div className="border-b border-zinc-100 px-6 py-3">
              <label className="block text-xs font-semibold uppercase tracking-wide text-zinc-500">
                Title
              </label>
              <input
                type="text"
                value={refinedTitle}
                onChange={(e) => setRefinedTitle(e.target.value)}
                className="mt-1 w-full max-w-xl rounded-md border border-zinc-200 px-3 py-2 text-sm text-zinc-900"
              />
              <p className="mt-2 text-xs text-zinc-500">
                Snapshot: <strong>{allRows.length}</strong> rows in memory
                {savedIdParam ? "" : ` (draft; max ${MAX_DRAFT_ROWS} rows stored in session)`} · Filtered:{" "}
                <strong>{filteredRows.length}</strong>
              </p>
            </div>

            <div className="flex shrink-0 gap-1 border-b border-zinc-100 px-6 pt-2">
              {(["data", "sql"] as const).map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTab(t)}
                  className={`rounded-t-md px-4 py-2 text-xs font-semibold capitalize ${
                    tab === t
                      ? "border border-b-white border-zinc-200 bg-white text-zinc-900"
                      : "text-zinc-500 hover:text-zinc-800"
                  }`}
                >
                  {t === "data" ? "Data" : "SQL"}
                </button>
              ))}
            </div>

            <div className="min-h-0 flex-1 overflow-auto p-6">
              {tab === "sql" ? (
                <pre className="whitespace-pre-wrap rounded-lg border border-zinc-200 bg-zinc-950 p-4 font-mono text-xs leading-relaxed text-zinc-100">
                  {composedSql}
                </pre>
              ) : (
                <>
                  <div className="mb-4 rounded-lg border border-zinc-200 bg-zinc-50 p-4">
                    <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                      <span className="text-xs font-semibold uppercase tracking-wide text-zinc-600">
                        Filters (offline)
                      </span>
                      <button
                        type="button"
                        onClick={addFilter}
                        disabled={columns.length === 0}
                        className="inline-flex items-center gap-1 rounded-md border border-zinc-300 bg-white px-2 py-1 text-xs font-semibold text-zinc-800 hover:bg-zinc-100 disabled:opacity-50"
                      >
                        <Plus size={14} aria-hidden /> Add filter
                      </button>
                    </div>
                    {filters.length === 0 ? (
                      <p className="text-xs text-zinc-500">No filters — showing all snapshot rows.</p>
                    ) : (
                      <ul className="space-y-2">
                        {filters.map((f) => (
                          <li
                            key={f.id}
                            className="flex flex-wrap items-end gap-2 rounded-md border border-zinc-200 bg-white p-2"
                          >
                            <label className="text-[11px] text-zinc-500">
                              Column
                              <select
                                value={f.column}
                                onChange={(e) => updateFilter(f.id, { column: e.target.value })}
                                className="mt-0.5 block rounded border border-zinc-200 px-2 py-1 text-xs"
                              >
                                {columns.map((c) => (
                                  <option key={c} value={c}>
                                    {c}
                                  </option>
                                ))}
                              </select>
                            </label>
                            <label className="text-[11px] text-zinc-500">
                              Operator
                              <select
                                value={f.op}
                                onChange={(e) =>
                                  updateFilter(f.id, { op: e.target.value as RecordFilterRow["op"] })
                                }
                                className="mt-0.5 block rounded border border-zinc-200 px-2 py-1 text-xs"
                              >
                                {RECORD_FILTER_OPS.map((o) => (
                                  <option key={o.value} value={o.value}>
                                    {o.label}
                                  </option>
                                ))}
                              </select>
                            </label>
                            {f.op !== "isEmpty" && f.op !== "isNotEmpty" && (
                              <label className="min-w-[8rem] flex-1 text-[11px] text-zinc-500">
                                Value
                                <input
                                  type="text"
                                  value={f.value}
                                  onChange={(e) => updateFilter(f.id, { value: e.target.value })}
                                  className="mt-0.5 w-full rounded border border-zinc-200 px-2 py-1 text-xs"
                                />
                              </label>
                            )}
                            <button
                              type="button"
                              onClick={() => removeFilter(f.id)}
                              className="rounded p-1 text-red-600 hover:bg-red-50"
                              aria-label="Remove filter"
                            >
                              <Trash2 size={16} />
                            </button>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>

                  <div className="overflow-x-auto rounded-lg border border-zinc-200">
                    <table className="w-full min-w-[640px] text-xs">
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
                        {filteredRows.slice(0, 500).map((row, i) => (
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
                    {filteredRows.length > 500 && (
                      <p className="border-t border-zinc-100 px-3 py-2 text-[11px] text-zinc-500">
                        Showing first 500 of {filteredRows.length} filtered rows.
                      </p>
                    )}
                  </div>
                </>
              )}
            </div>
          </>
        )}

        {saveModalOpen && (
          <div
            className="fixed inset-0 z-200 flex items-center justify-center bg-zinc-950/60 p-4"
            role="dialog"
            aria-modal="true"
            aria-label="Save view"
          >
            <div className="w-full max-w-md rounded-xl border border-zinc-200 bg-white p-6 shadow-xl">
              <h2 className="text-sm font-bold text-zinc-900">Save view</h2>
              <p className="mt-1 text-xs text-zinc-500">
                Persists the full snapshot ({allRows.length} rows), filters, and display SQL to the library.
              </p>
              <label className="mt-4 block text-xs font-semibold text-zinc-600">Name</label>
              <input
                type="text"
                value={saveTitle}
                onChange={(e) => setSaveTitle(e.target.value)}
                className="mt-1 w-full rounded-md border border-zinc-200 px-3 py-2 text-sm"
              />
              {saveError && <p className="mt-2 text-xs text-red-700">{saveError}</p>}
              <div className="mt-4 flex justify-end gap-2">
                <button
                  type="button"
                  className="rounded-md border border-zinc-300 px-3 py-1.5 text-xs font-semibold text-zinc-800"
                  onClick={() => setSaveModalOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={saving}
                  className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
                  onClick={() => void submitSave()}
                >
                  {saving ? "Saving…" : "Save"}
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
