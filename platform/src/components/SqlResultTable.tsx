interface SqlResultTableProps {
  columns: string[];
  rows: Record<string, unknown>[];
}

export function SqlResultTable({ columns, rows }: SqlResultTableProps) {
  if (columns.length === 0) {
    return (
      <div className="flex items-center justify-center rounded-lg border border-dashed p-8 text-sm text-muted-foreground">
        결과가 없습니다
      </div>
    );
  }

  return (
    <div className="rounded-lg border overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground w-10">
                #
              </th>
              {columns.map((col) => (
                <th key={col} className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="border-b last:border-0 hover:bg-muted/30 transition-colors">
                <td className="px-3 py-2 text-xs text-muted-foreground">{i + 1}</td>
                {columns.map((col) => (
                  <td key={col} className="px-3 py-2">
                    {String(row[col] ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="border-t bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
        {rows.length}개 행
      </div>
    </div>
  );
}
