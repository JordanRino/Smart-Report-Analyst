export function SqlTable({ data, query }: { data: any[]; query: string }) {
  if (!data?.length) return <div className="p-4 text-zinc-500">No results found.</div>;

  const columns = Object.keys(data[0]);

  return (
    <div className="my-4 overflow-hidden rounded-lg border border-zinc-200 bg-white shadow-sm">
      <div className="bg-zinc-50 px-4 py-2 border-b">
        <code className="text-xs text-zinc-500 block truncate">{query}</code>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="bg-zinc-50 text-zinc-600">
            <tr>
              {columns.map((col) => (
                <th key={col} className="px-4 py-2 font-medium capitalize">{col.replace(/_/g, ' ')}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100">
            {data.slice(0, 5).map((row, i) => (
              <tr key={i} className="hover:bg-zinc-50 transition-colors">
                {columns.map((col) => (
                  <td key={col} className="px-4 py-2 text-zinc-700">{String(row[col])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.length > 5 && (
        <div className="p-2 text-center border-t bg-zinc-50 text-xs text-zinc-400">
          + {data.length - 5} more rows
        </div>
      )}
    </div>
  );
}