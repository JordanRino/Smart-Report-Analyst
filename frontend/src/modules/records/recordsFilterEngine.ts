import type { RecordFilterOp, RecordFilterRow } from "@/modules/records/recordsFilterTypes";

function cellIsEmpty(v: unknown): boolean {
  if (v == null) return true;
  if (typeof v === "string") return v.trim().length === 0;
  return false;
}

function toFiniteNumber(v: unknown): number | null {
  if (typeof v === "number" && Number.isFinite(v)) return v;
  if (typeof v === "string" && v.trim() !== "") {
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  }
  return null;
}

function matchOne(row: Record<string, unknown>, f: RecordFilterRow): boolean {
  const raw = f.column ? row[f.column] : undefined;

  switch (f.op) {
    case "isEmpty":
      return cellIsEmpty(raw);
    case "isNotEmpty":
      return !cellIsEmpty(raw);
    case "eq":
      return String(raw ?? "") === f.value;
    case "ne":
      return String(raw ?? "") !== f.value;
    case "contains": {
      const s = String(raw ?? "").toLowerCase();
      return s.includes(f.value.toLowerCase());
    }
    case "gt":
    case "gte":
    case "lt":
    case "lte": {
      const a = toFiniteNumber(raw);
      const b = toFiniteNumber(f.value);
      if (a == null || b == null) return false;
      if (f.op === "gt") return a > b;
      if (f.op === "gte") return a >= b;
      if (f.op === "lt") return a < b;
      return a <= b;
    }
    default:
      return true;
  }
}

/** Union of object keys across rows (stable order: first row keys first, then extras). */
export function columnUnion(rows: Record<string, unknown>[]): string[] {
  if (rows.length === 0) return [];
  const seen = new Set<string>();
  const out: string[] = [];
  for (const row of rows) {
    for (const k of Object.keys(row)) {
      if (!seen.has(k)) {
        seen.add(k);
        out.push(k);
      }
    }
  }
  return out;
}

export function applyOfflineFilters(
  rows: Record<string, unknown>[],
  filters: RecordFilterRow[],
): Record<string, unknown>[] {
  if (filters.length === 0) return rows;
  return rows.filter((row) => filters.every((f) => matchOne(row, f)));
}

function sqlEscapeIdent(name: string): string {
  return "`" + name.replace(/`/g, "``") + "`";
}

function sqlEscapeString(s: string): string {
  return "'" + s.replace(/'/g, "''") + "'";
}

function opLabel(op: RecordFilterOp): string {
  const m: Record<RecordFilterOp, string> = {
    eq: "=",
    ne: "!=",
    contains: "LIKE",
    gt: ">",
    gte: ">=",
    lt: "<",
    lte: "<=",
    isEmpty: "IS EMPTY",
    isNotEmpty: "IS NOT EMPTY",
  };
  return m[op] ?? op;
}

/** Display-only SQL (not executed). */
export function buildComposedSqlDisplay(baseSql: string, filters: RecordFilterRow[]): string {
  const lines: string[] = [
    "-- Display-only composition; rows are filtered in the browser from the snapshot.",
    "SELECT *",
    "FROM (",
  ];
  const indented = (baseSql || "").trimEnd().split("\n");
  for (const line of indented) {
    lines.push(`  ${line}`);
  }
  lines.push(") AS `_snapshot`");
  if (filters.length === 0) {
    lines.push(";");
    return lines.join("\n");
  }
  lines.push("WHERE 1 = 1");
  for (const f of filters) {
    if (!f.column) continue;
    const col = sqlEscapeIdent(f.column);
    if (f.op === "isEmpty") {
      lines.push(`  AND (${col} IS NULL OR TRIM(CAST(${col} AS CHAR)) = '')`);
    } else if (f.op === "isNotEmpty") {
      lines.push(`  AND (${col} IS NOT NULL AND TRIM(CAST(${col} AS CHAR)) <> '')`);
    } else if (f.op === "contains") {
      const pat = "%" + f.value.replace(/\\/g, "\\\\").replace(/%/g, "\\%").replace(/_/g, "\\_") + "%";
      lines.push(`  AND ${col} LIKE ${sqlEscapeString(pat)} ESCAPE '\\\\'`);
    } else if (f.op === "eq") {
      lines.push(`  AND CAST(${col} AS CHAR) = ${sqlEscapeString(f.value)}`);
    } else if (f.op === "ne") {
      lines.push(`  AND CAST(${col} AS CHAR) <> ${sqlEscapeString(f.value)}`);
    } else if (f.op === "gt" || f.op === "gte" || f.op === "lt" || f.op === "lte") {
      const sym = opLabel(f.op);
      lines.push(`  AND ${col} ${sym} ${sqlEscapeString(f.value)}`);
    }
  }
  lines.push(";");
  return lines.join("\n");
}

export function formatFiltersForDiscuss(filters: RecordFilterRow[]): string {
  if (filters.length === 0) return "(none)";
  return filters
    .map((f) => {
      if (f.op === "isEmpty" || f.op === "isNotEmpty") {
        return `- **${f.column}** — ${f.op}`;
      }
      return `- **${f.column}** ${opLabel(f.op)} ${JSON.stringify(f.value)}`;
    })
    .join("\n");
}
