"use client";

import { useEffect, useRef, useState } from "react";
import { getApiPrefix } from "@/lib/env";

type Props = {
  status: string;
  query: string;
  results: unknown;
  refinedUserQuestion?: string;
  rowCount?: number;
};

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
  const fetchedKey = useRef<string | null>(null);

  useEffect(() => {
    if (status !== "complete") {
      fetchedKey.current = null;
      return;
    }
    const rows = Array.isArray(results) ? results : [];
    const key = `${query}\0${rows.length}\0${refinedUserQuestion ?? ""}`;
    if (!query.trim() && rows.length === 0) {
      return;
    }
    if (fetchedKey.current === key) {
      return;
    }
    fetchedKey.current = key;

    let cancelled = false;
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
          if (!cancelled) setError(msg);
          return;
        }
        if (!ct.includes("application/pdf")) {
          if (!cancelled) setError("Server did not return a PDF");
          return;
        }
        const blob = await res.blob();
        if (cancelled) return;
        const url = URL.createObjectURL(blob);
        setPdfUrl(url);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Network error");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [status, query, results, refinedUserQuestion, rowCount]);

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
