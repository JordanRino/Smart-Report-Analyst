/** Offline filter operators (client-side only; SQL tab is display-only). */
export type RecordFilterOp =
  | "eq"
  | "ne"
  | "contains"
  | "gt"
  | "gte"
  | "lt"
  | "lte"
  | "isEmpty"
  | "isNotEmpty";

export interface RecordFilterRow {
  id: string;
  column: string;
  op: RecordFilterOp;
  /** Ignored for isEmpty / isNotEmpty */
  value: string;
}

export const RECORD_FILTER_OPS: { value: RecordFilterOp; label: string }[] = [
  { value: "eq", label: "equals" },
  { value: "ne", label: "not equals" },
  { value: "contains", label: "contains" },
  { value: "gt", label: ">" },
  { value: "gte", label: ">=" },
  { value: "lt", label: "<" },
  { value: "lte", label: "<=" },
  { value: "isEmpty", label: "is empty" },
  { value: "isNotEmpty", label: "is not empty" },
];
