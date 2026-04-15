"use client";

import { useApp } from "@/providers/AppContext";
import { getApiPrefix } from "@/lib/env";
import { Save } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";

type Props = {
  status: string;
  query: string;
  results: unknown;
  refinedUserQuestion?: string;
  rowCount?: number;
};

/** Cheap fingerprint so we do not depend on ``results`` reference identity in the effect. */
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

function isPdfType(blob: Blob): Promise<boolean> {
  return blob.slice(0, 4).arrayBuffer().then((buf) => {
    const b = new Uint8Array(buf);
    return b.length >= 4 && b[0] === 0x25 && b[1] === 0x50 && b[2] === 0x44 && b[3] === 0x46;
  });
}

/** CopilotKit ``execute_sql`` completion: PDF from API + save to reports library. */
export function SqlResultPdfReport({
  status,
  query,
  results,
  refinedUserQuestion,
  rowCount,
}: Props) {
  const { effectiveThreadId, pickedAgentId, orchestratorMainAgentId } = useApp();
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [savingReport, setSavingReport] = useState(false);
  const [saveReportMessage, setSaveReportMessage] = useState<string | null>(null);
  /** Set only after a successful blob → object URL (avoids Strict Mode / dedupe deadlock). */
  const succeededKeyRef = useRef<string | null>(null);

  const rows = Array.isArray(results) ? results : [];
  const resultsFingerprintValue = resultsFingerprint(rows);
  const fetchKey = useMemo(
    () =>
      `${query}\0${resultsFingerprintValue}\0${refinedUserQuestion ?? ""}\0${rowCount ?? ""}`,
    [query, resultsFingerprintValue, refinedUserQuestion, rowCount],
  );

  useEffect(() => {
    if (status !== "complete") {
      succeededKeyRef.current = null;
      return;
    }
    if (!query.trim() && rows.length === 0) {
      return;
    }
    if (succeededKeyRef.current === fetchKey) {
      return;
    }

    const ac = new AbortController();
    setLoading(true);
    setError(null);
    setPdfUrl(null);

    const body = {
      executed_sql: query,
      results: rows,
      refined_user_question: refinedUserQuestion || undefined,
      row_count: rowCount,
    };

    void (async () => {
      try {
        const res = await fetch(`${getApiPrefix()}/reports/pdf`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
          signal: ac.signal,
        });
        const ct = res.headers.get("content-type") || "";
        if (!res.ok) {
          let msg = `Request failed (${res.status})`;
          if (ct.includes("application/json")) {
            try {
              const j = (await res.json()) as { detail?: string | unknown[] };
              const d = j.detail;
              if (typeof d === "string") msg = d;
              else if (Array.isArray(d) && d.length > 0) {
                const first = d[0] as { msg?: string };
                if (typeof first?.msg === "string") msg = first.msg;
              }
            } catch {
              /* ignore */
            }
          }
          if (!ac.signal.aborted) setError(msg);
          return;
        }
        const blob = await res.blob();
        if (ac.signal.aborted) return;
        const pdfOk =
          ct.includes("application/pdf") || (await isPdfType(blob));
        if (!pdfOk) {
          if (!ac.signal.aborted) setError("Server did not return a PDF");
          return;
        }
        const url = URL.createObjectURL(blob);
        if (ac.signal.aborted) {
          URL.revokeObjectURL(url);
          return;
        }
        succeededKeyRef.current = fetchKey;
        setPdfUrl(url);
      } catch (e) {
        if (ac.signal.aborted) return;
        setError(e instanceof Error ? e.message : "Network error");
      } finally {
        if (!ac.signal.aborted) setLoading(false);
      }
    })();

    return () => {
      ac.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- stable via fetchKey
  }, [status, fetchKey]);

  useEffect(() => {
    return () => {
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    };
  }, [pdfUrl]);

  useEffect(() => {
    setPreviewOpen(false);
  }, [pdfUrl]);

  useEffect(() => {
    setSaveReportMessage(null);
  }, [fetchKey]);

  useEffect(() => {
    if (!previewOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setPreviewOpen(false);
    };
    window.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [previewOpen]);

  if (status === "inProgress") {
    return (
      <div className="my-4 rounded-lg border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm text-zinc-600">
        Running SQL…
      </div>
    );
  }

  if (status !== "complete") {
    return null;
  }

  if (loading) {
    return (
      <div className="my-4 rounded-lg border border-zinc-200 bg-white px-4 py-3 text-sm text-zinc-600">
        Building PDF report…
      </div>
    );
  }

  if (error) {
    return (
      <div className="my-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
        {error}
      </div>
    );
  }

  if (!pdfUrl) {
    return null;
  }

  const fileSlug = (refinedUserQuestion || "sba-report").replace(/[^a-zA-Z0-9_-]+/g, "-").slice(0, 48) || "report";

  async function handleSaveReport() {
    setSavingReport(true);
    setSaveReportMessage(null);
    try {
      const res = await fetch(`${getApiPrefix()}/reports/saved`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          executed_sql: query,
          results: rows,
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
        let msg = `Save failed (${res.status})`;
        const ct = res.headers.get("content-type") || "";
        if (ct.includes("application/json")) {
          try {
            const j = (await res.json()) as { detail?: string | unknown[] };
            const d = j.detail;
            if (typeof d === "string") msg = d;
            else if (Array.isArray(d) && d.length > 0) {
              const first = d[0] as { msg?: string };
              if (typeof first?.msg === "string") msg = first.msg;
            }
          } catch {
            /* ignore */
          }
        }
        setSaveReportMessage(msg);
        return;
      }
      setSaveReportMessage("Saved to Reports.");
    } catch (e) {
      setSaveReportMessage(e instanceof Error ? e.message : "Network error");
    } finally {
      setSavingReport(false);
    }
  }

  const overlay =
    previewOpen &&
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
          onClick={() => setPreviewOpen(false)}
        />
        <div className="relative z-10 flex h-[min(88vh,900px)] w-full max-w-5xl flex-col overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-2xl">
          <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-zinc-100 bg-zinc-50 px-4 py-3">
            <span className="text-sm font-medium text-zinc-800">Report preview</span>
            <div className="flex flex-wrap items-center gap-2">
              <a
                href={pdfUrl}
                download={`${fileSlug}.pdf`}
                className="rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-xs font-semibold text-zinc-800 hover:bg-zinc-100"
              >
                Download
              </a>
              <button
                type="button"
                className="rounded-md bg-zinc-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-zinc-800"
                onClick={() => setPreviewOpen(false)}
              >
                Close
              </button>
            </div>
          </div>
          <div className="min-h-0 flex-1 bg-zinc-100">
            <object
              data={pdfUrl}
              type="application/pdf"
              className="h-full w-full min-h-[400px]"
              title="Report preview"
            >
              <p className="p-4 text-sm text-zinc-600">
                Preview not available in this browser. Use Download.
              </p>
            </object>
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
            <span className="text-sm font-medium text-zinc-800">Analysis report</span>
            <button
              type="button"
              className="rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-xs font-semibold text-zinc-800 hover:bg-zinc-100"
              onClick={() => setPreviewOpen(true)}
            >
              Preview
            </button>
            <a
              href={pdfUrl}
              download={`${fileSlug}.pdf`}
              className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700"
            >
              Download PDF
            </a>
            <button
              type="button"
              disabled={savingReport}
              className="inline-flex items-center gap-1 rounded-md border border-amber-300 bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-950 hover:bg-amber-100 disabled:opacity-60"
              onClick={() => void handleSaveReport()}
            >
              <Save size={14} aria-hidden />
              {savingReport ? "Saving…" : "Save report"}
            </button>
          </div>
          {saveReportMessage ? (
            <p
              className={`text-xs ${saveReportMessage.startsWith("Saved") ? "text-green-700" : "text-red-700"}`}
            >
              {saveReportMessage}
            </p>
          ) : null}
        </div>
      </div>
      {overlay}
    </>
  );
}
