"use client";

import { useApp } from "@/providers/AppContext";
import { getApiPrefix } from "@/lib/env";
import { Download, Save, Eye } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

type Props = {
  status: string;
  temp_id: string;
  title: string;
  markdown_content?: string;
};

/** Renders a PDF report card delivered by the orchestrator's generate_report_pdf tool. */
export function ReportBuilderCard({ status, temp_id, title }: Props) {
  const { effectiveThreadId, pickedAgentId, orchestratorMainAgentId } = useApp();

  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [savedMeta, setSavedMeta] = useState<{ id: string } | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const savedRef = useRef(false);

  // Fetch the PDF from the temp store as soon as the action completes.
  useEffect(() => {
    if (status !== "complete" || !temp_id) return;
    const ac = new AbortController();
    void (async () => {
      try {
        const res = await fetch(`${getApiPrefix()}/reports/temp/${encodeURIComponent(temp_id)}`, {
          signal: ac.signal,
        });
        if (!res.ok) {
          if (!ac.signal.aborted) setLoadError(`Could not load report (${res.status})`);
          return;
        }
        const blob = await res.blob();
        if (ac.signal.aborted) return;
        const url = URL.createObjectURL(blob);
        setPdfUrl(url);
      } catch (e) {
        if (!ac.signal.aborted)
          setLoadError(e instanceof Error ? e.message : "Network error");
      }
    })();
    return () => {
      ac.abort();
    };
  }, [status, temp_id]);

  // Revoke object URL on unmount.
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

  const handleSave = useCallback(async () => {
    if (saving || savedMeta || savedRef.current) return;
    setSaving(true);
    setSaveError(null);
    try {
      const res = await fetch(`${getApiPrefix()}/reports/temp/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          temp_id,
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
      savedRef.current = true;
      setSavedMeta(data);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Network error");
    } finally {
      setSaving(false);
    }
  }, [saving, savedMeta, temp_id, effectiveThreadId, pickedAgentId, orchestratorMainAgentId]);

  if (status === "inProgress") {
    return (
      <div className="my-4 rounded-lg border border-indigo-100 bg-indigo-50 px-4 py-3 text-sm text-indigo-700">
        Building report…
      </div>
    );
  }
  if (status !== "complete") return null;

  const fileSlug = title.replace(/[^a-zA-Z0-9_-]+/g, "-").slice(0, 48) || "report";

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
            <span className="text-sm font-medium text-zinc-800">{title || "Report preview"}</span>
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
                <span className="ml-1.5 text-xs font-normal text-zinc-500">— {title}</span>
              )}
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
                    disabled={saving || !pdfUrl}
                    className="inline-flex items-center gap-1 rounded-md border border-amber-300 bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-950 hover:bg-amber-100 disabled:opacity-60"
                    onClick={() => void handleSave()}
                  >
                    <Save size={13} aria-hidden /> {saving ? "Saving…" : "Save report"}
                  </button>
                )}
              </>
            )}
          </div>
          {saveError && <p className="text-xs text-red-700">{saveError}</p>}
        </div>
      </div>
      {overlay}
    </>
  );
}
