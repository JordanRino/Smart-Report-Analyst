"use client";

import { getApiPrefix } from "@/lib/env";
import { Download, Eye } from "lucide-react";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

type Props = {
  status: string;
  report_id: string;
  title: string;
};

/**
 * Renders a PDF report card delivered by the orchestrator's generate_report_pdf tool.
 *
 * The report is auto-saved permanently — no Save button needed. The card fetches
 * the PDF from the permanent store (/api/reports/saved/{id}/file), so it survives
 * navigation and history replay without any temp-store dependency.
 */
export function ReportBuilderCard({ status, report_id, title }: Props) {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);

  useEffect(() => {
    if (status !== "complete" || !report_id) return;
    const ac = new AbortController();
    void (async () => {
      try {
        const res = await fetch(
          `${getApiPrefix()}/reports/saved/${encodeURIComponent(report_id)}/file`,
          { signal: ac.signal },
        );
        if (!res.ok) {
          if (!ac.signal.aborted)
            setLoadError(`Could not load report (${res.status})`);
          return;
        }
        const blob = await res.blob();
        if (ac.signal.aborted) return;
        setPdfUrl(URL.createObjectURL(blob));
      } catch (e) {
        if (!ac.signal.aborted)
          setLoadError(e instanceof Error ? e.message : "Network error");
      }
    })();
    return () => ac.abort();
  }, [status, report_id]);

  useEffect(() => {
    return () => {
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    };
  }, [pdfUrl]);

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

  if (status === "inProgress") {
    return (
      <div className="my-4 rounded-lg border border-indigo-100 bg-indigo-50 px-4 py-3 text-sm text-indigo-700">
        Building report…
      </div>
    );
  }
  if (status !== "complete") return null;

  const fileSlug =
    title.replace(/[^a-zA-Z0-9_-]+/g, "-").slice(0, 48) || "report";

  const overlay =
    previewOpen &&
    pdfUrl &&
    typeof document !== "undefined" &&
    createPortal(
      <div
        className="fixed inset-0 z-200 flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        aria-label="Report preview"
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
              {title || "Report preview"}
            </span>
            <div className="flex gap-2">
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
      <div className="my-4 overflow-hidden rounded-lg border border-indigo-200 bg-white shadow-sm">
        <div className="flex flex-col gap-2 border-b border-indigo-100 bg-indigo-50 px-4 py-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-sm font-medium text-zinc-800">
              Report
              {title && (
                <span className="ml-1.5 text-xs font-normal text-zinc-500">
                  — {title}
                </span>
              )}
            </span>
            {/* Report is auto-saved — show a permanent saved badge */}
            <span className="rounded border border-green-300 bg-green-50 px-2 py-0.5 text-[10px] font-semibold text-green-700">
              Saved to dashboard
            </span>
            {loadError ? (
              <span className="text-xs text-red-600">{loadError}</span>
            ) : (
              <>
                <button
                  type="button"
                  disabled={!pdfUrl}
                  className="inline-flex items-center gap-1 rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-xs font-semibold text-zinc-800 hover:bg-zinc-100 disabled:opacity-50"
                  onClick={() => setPreviewOpen(true)}
                >
                  <Eye size={13} aria-hidden /> Preview
                </button>
                {pdfUrl ? (
                  <a
                    href={pdfUrl}
                    download={`${fileSlug}.pdf`}
                    className="inline-flex items-center gap-1 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700"
                  >
                    <Download size={13} aria-hidden /> Download PDF
                  </a>
                ) : (
                  <span className="text-xs text-zinc-400">Loading PDF…</span>
                )}
              </>
            )}
          </div>
        </div>
      </div>
      {overlay}
    </>
  );
}
