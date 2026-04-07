"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { getApiPrefix } from "@/lib/env";

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

/** Renders CopilotKit ``execute_sql`` completion: fetches PDF from API, download + preview. */
export function SqlPdfReport({
  status,
  query,
  results,
  refinedUserQuestion,
  rowCount,
}: Props) {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  /** Set only after a successful blob → object URL (avoids Strict Mode / dedupe deadlock). */
  const succeededKeyRef = useRef<string | null>(null);

  const fetchKey = useMemo(() => {
    const rows = Array.isArray(results) ? results : [];
    const fp = resultsFingerprint(rows);
    return `${query}\0${fp}\0${refinedUserQuestion ?? ""}\0${rowCount ?? ""}`;
  }, [query, results, refinedUserQuestion, rowCount]);

  useEffect(() => {
    if (status !== "complete") {
      succeededKeyRef.current = null;
      return;
    }
    const rows = Array.isArray(results) ? results : [];
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
      setLoading(false);
    };
  }, [status, fetchKey]);

  useEffect(() => {
    return () => {
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    };
  }, [pdfUrl]);

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

  return (
    <div className="my-4 overflow-hidden rounded-lg border border-zinc-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-center gap-3 border-b border-zinc-100 bg-zinc-50 px-4 py-3">
        <span className="text-sm font-medium text-zinc-800">Analysis report</span>
        <a
          href={pdfUrl}
          download={`${fileSlug}.pdf`}
          className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700"
        >
          Download PDF
        </a>
      </div>
      <div className="h-[min(70vh,520px)] w-full bg-zinc-100">
        <object
          data={pdfUrl}
          type="application/pdf"
          className="h-full w-full"
          title="Report preview"
        >
          <p className="p-4 text-sm text-zinc-600">
            Preview not available in this browser. Use Download PDF.
          </p>
        </object>
      </div>
    </div>
  );
}
