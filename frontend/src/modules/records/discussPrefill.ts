import { formatFiltersForDiscuss } from "@/modules/records/recordsFilterEngine";
import type { RecordFilterRow } from "@/modules/records/recordsFilterTypes";

export function buildDiscussPrefillText(params: {
  title: string;
  baseSql: string;
  filters: RecordFilterRow[];
  composedSql: string;
  filteredRowCount: number;
  totalRowCount: number;
  savedRecordId?: string | null;
}): string {
  const idLine = params.savedRecordId
    ? `Saved record id: \`${params.savedRecordId}\``
    : "Draft (not saved to the library yet).";

  return [
    `## Records view: ${params.title}`,
    "",
    idLine,
    "",
    "**Row counts (after offline filters):**",
    `- Showing **${params.filteredRowCount}** of **${params.totalRowCount}** rows in this snapshot.`,
    "",
    "**Base SQL (from when the query was run):**",
    "```sql",
    params.baseSql.trim() || "(empty)",
    "```",
    "",
    "**Filters applied (offline on snapshot):**",
    formatFiltersForDiscuss(params.filters),
    "",
    "**Effective SQL (display only; not re-run on the server):**",
    "```sql",
    params.composedSql.trim(),
    "```",
    "",
    "What would you like to explore or change next?",
  ].join("\n");
}
