import { useEffect, useState } from "react";

export interface DataTableColumn<T> {
  key: keyof T | string;
  header: string;
  render?: (row: T) => React.ReactNode;
  width?: string;
}

interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
  data: T[];
  rowKey: keyof T;
  emptyMessage?: string;
  onRowClick?: (row: T) => void;
}

function useWindowWidth(): number {
  const [width, setWidth] = useState(window.innerWidth);
  useEffect(() => {
    const handler = () => setWidth(window.innerWidth);
    window.addEventListener("resize", handler);
    return () => window.removeEventListener("resize", handler);
  }, []);
  return width;
}

function getCellValue<T>(
  row: T,
  key: string,
  render?: (row: T) => React.ReactNode,
): React.ReactNode {
  if (render) return render(row);
  return String((row as Record<string, unknown>)[key] ?? "—");
}

export default function DataTable<T>({
  columns,
  data,
  rowKey,
  emptyMessage = "No data available.",
  onRowClick,
}: DataTableProps<T>) {
  const width = useWindowWidth();
  const isCard = width < 900;

  if (data.length === 0) {
    return (
      <div
        style={{
          padding: "24px",
          textAlign: "center",
          fontSize: "12px",
          color: "var(--color-neutral-400)",
        }}
      >
        {emptyMessage}
      </div>
    );
  }

  // Card-stack layout — below 900px
  if (isCard) {
    return (
      <div
        className="subop-datatable-cards"
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "10px",
          padding: "12px",
        }}
      >
        {data.map((row) => (
          <div
            key={String(row[rowKey])}
            onClick={() => onRowClick?.(row)}
            style={{
              background: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              borderRadius: "8px",
              padding: "12px 14px",
              cursor: onRowClick ? "pointer" : "default",
              display: "flex",
              flexDirection: "column",
              gap: "6px",
              boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
            }}
          >
            {columns.map((col) => (
              <div
                key={String(col.key)}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                <span
                  style={{
                    fontSize: "10px",
                    fontWeight: 600,
                    color: "var(--color-neutral-500)",
                    textTransform: "uppercase",
                    letterSpacing: "0.5px",
                    flexShrink: 0,
                  }}
                >
                  {col.header}
                </span>
                <span
                  style={{
                    fontSize: "12px",
                    color: "var(--color-neutral-dark)",
                    textAlign: "right",
                  }}
                >
                  {getCellValue(row, String(col.key), col.render)}
                </span>
              </div>
            ))}
          </div>
        ))}
      </div>
    );
  }

  // Default table layout — 900px and above
  return (
    <div className="subop-datatable-table" style={{ overflowX: "auto" }}>
      <table
        style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}
      >
        <thead>
          <tr
            style={{
              background: "var(--color-neutral-light)",
              borderBottom: "1px solid var(--color-border)",
            }}
          >
            {columns.map((col) => (
              <th
                key={String(col.key)}
                style={{
                  padding: "8px 12px",
                  textAlign: "left",
                  fontWeight: 600,
                  fontSize: "11px",
                  color: "var(--color-neutral-500)",
                  textTransform: "uppercase",
                  letterSpacing: "0.5px",
                  whiteSpace: "nowrap",
                  width: col.width,
                }}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr
              key={String(row[rowKey])}
              onClick={() => onRowClick?.(row)}
              style={{
                borderBottom: "1px solid var(--color-border)",
                backgroundColor:
                  i % 2 === 1 ? "var(--color-row-alt)" : "transparent",
                cursor: onRowClick ? "pointer" : "default",
                transition: "background-color 0.1s",
              }}
              onMouseEnter={(e) => {
                if (onRowClick)
                  (
                    e.currentTarget as HTMLTableRowElement
                  ).style.backgroundColor = "var(--color-neutral-light)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLTableRowElement).style.backgroundColor =
                  i % 2 === 1 ? "var(--color-row-alt)" : "transparent";
              }}
            >
              {columns.map((col) => (
                <td
                  key={String(col.key)}
                  style={{
                    padding: "10px 12px",
                    color: "var(--color-neutral-dark)",
                    verticalAlign: "middle",
                  }}
                >
                  {getCellValue(row, String(col.key), col.render)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
