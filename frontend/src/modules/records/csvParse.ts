/** Parse CSV text into header + data rows (RFC-style quoting). */
export function parseCsvToRows(csv: string): { columns: string[]; rows: string[][] } {
  const lines = csv.trim().split("\n");
  if (lines.length === 0) return { columns: [], rows: [] };
  const splitLine = (line: string) => {
    const result: string[] = [];
    let cur = "";
    let inQuote = false;
    for (let i = 0; i < line.length; i++) {
      const ch = line[i];
      if (ch === '"') {
        if (inQuote && line[i + 1] === '"') {
          cur += '"';
          i++;
        } else inQuote = !inQuote;
      } else if (ch === "," && !inQuote) {
        result.push(cur);
        cur = "";
      } else {
        cur += ch;
      }
    }
    result.push(cur);
    return result;
  };
  const columns = splitLine(lines[0]);
  const rows = lines.slice(1).map(splitLine);
  return { columns, rows };
}

export function csvRowsToObjects(columns: string[], rows: string[][]): Record<string, unknown>[] {
  return rows.map((r) => {
    const o: Record<string, unknown> = {};
    columns.forEach((c, i) => {
      o[c] = r[i] ?? "";
    });
    return o;
  });
}
