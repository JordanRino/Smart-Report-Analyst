import type { RecordFilterRow } from "@/modules/records/recordsFilterTypes";

export const RECORDS_DRAFT_STORAGE_KEY = "sra:recordsDraft:v1";
export const MAX_DRAFT_ROWS = 2000;

export interface RecordsDraftV1 {
  version: 1;
  baseSql: string;
  rows: Record<string, unknown>[];
  refinedUserQuestion?: string | null;
  rowCount?: number | null;
  filters: RecordFilterRow[];
  /** When opened from a saved record, for Save / Discuss context */
  sourceSavedId?: string | null;
}

export function readDraft(): RecordsDraftV1 | null {
  if (typeof sessionStorage === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(RECORDS_DRAFT_STORAGE_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw) as RecordsDraftV1;
    if (data?.version !== 1 || !Array.isArray(data.rows)) return null;
    if (!Array.isArray(data.filters)) data.filters = [];
    return data;
  } catch {
    return null;
  }
}

export function writeDraft(draft: RecordsDraftV1): void {
  if (typeof sessionStorage === "undefined") return;
  const toStore: RecordsDraftV1 = {
    ...draft,
    rows: draft.rows.slice(0, MAX_DRAFT_ROWS),
  };
  sessionStorage.setItem(RECORDS_DRAFT_STORAGE_KEY, JSON.stringify(toStore));
}

export function clearDraft(): void {
  if (typeof sessionStorage === "undefined") return;
  sessionStorage.removeItem(RECORDS_DRAFT_STORAGE_KEY);
}
