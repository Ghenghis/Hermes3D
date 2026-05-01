import type { ReactNode } from "react";

/**
 * Dense data table per visual contract: sticky header, status-chip cells,
 * minimal borders. Generic over row type.
 *
 *  <DataTable
 *    columns={[{ id: "name", header: "Name", render: (r) => r.name }, ...]}
 *    rows={printers}
 *    keyOf={(r) => r.id}
 *  />
 */
export type Column<T> = {
  id: string;
  header: ReactNode;
  render: (row: T) => ReactNode;
  /** Tailwind width class, e.g. "w-32". Optional. */
  width?: string;
  /** "left" (default) / "right" / "center" alignment. */
  align?: "left" | "right" | "center";
};

const ALIGN = { left: "text-left", right: "text-right", center: "text-center" } as const;

export function DataTable<T>({
  columns,
  rows,
  keyOf,
  emptyLabel = "No data",
}: {
  columns: Column<T>[];
  rows: T[];
  keyOf: (row: T) => string;
  emptyLabel?: string;
}) {
  if (rows.length === 0) {
    return <div className="text-muted text-sm py-6 text-center">{emptyLabel}</div>;
  }
  return (
    <div className="w-full overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-muted text-xs uppercase tracking-wide border-b border-border">
            {columns.map((c) => (
              <th
                key={c.id}
                className={[
                  "py-2 px-2 font-medium",
                  ALIGN[c.align ?? "left"],
                  c.width ?? "",
                ].join(" ")}
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={keyOf(row)}
              className="border-b border-border/40 hover:bg-surface2 transition-colors"
            >
              {columns.map((c) => (
                <td
                  key={c.id}
                  className={["py-2 px-2 text-fg", ALIGN[c.align ?? "left"]].join(" ")}
                >
                  {c.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
