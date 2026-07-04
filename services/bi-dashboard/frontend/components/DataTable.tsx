import { useState } from 'react';

export interface Column {
  key: string;
  label: string;
  sortable?: boolean;
  width?: string;
}

interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
}

interface DataTableProps {
  /** Column definitions */
  columns: Column[];
  /** Row data — each object keyed to column keys */
  data: Record<string, unknown>[];
  /** Renders skeleton rows when true */
  isLoading?: boolean;
  /** Pagination config — omit to hide pagination */
  pagination?: PaginationProps;
  /** Called when a sortable column header is clicked */
  onSort?: (key: string, direction: 'asc' | 'desc' | null) => void;
}

type SortDirection = 'asc' | 'desc' | null;

/**
 * DataTable
 *
 * Shared table component used across Pipeline Monitor, Data Quality Dashboard,
 * Catalog Browser, and Admin Panel.
 *
 * Features:
 * - Column sort (asc → desc → unsorted) with direction indicator
 * - Row pagination with Showing N–M of Total text
 * - Loading skeleton — three grey placeholder rows (no spinner)
 * - Design tokens applied via CSS custom properties
 *
 * @param columns     - Column definitions
 * @param data        - Row data array
 * @param isLoading   - Shows skeleton rows when true
 * @param pagination  - Pagination config
 * @param onSort      - Sort callback
 */
export default function DataTable({
  columns,
  data,
  isLoading = false,
  pagination,
  onSort,
}: DataTableProps) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);

  const handleSort = (key: string) => {
    if (!onSort) return;
    let nextDirection: SortDirection;
    if (sortKey !== key) {
      nextDirection = 'asc';
    } else if (sortDirection === 'asc') {
      nextDirection = 'desc';
    } else {
      nextDirection = null;
    }
    setSortKey(nextDirection ? key : null);
    setSortDirection(nextDirection);
    onSort(key, nextDirection as 'asc' | 'desc');
  };

  const sortIcon = (key: string) => {
    if (sortKey !== key) return ' ↕';
    if (sortDirection === 'asc') return ' ↑';
    if (sortDirection === 'desc') return ' ↓';
    return ' ↕';
  };

  const start = pagination ? (pagination.page - 1) * pagination.pageSize + 1 : 1;
  const end = pagination ? Math.min(pagination.page * pagination.pageSize, pagination.total) : data.length;

  return (
    <div style={{ width: '100%' }}>
      <table
        style={{
          width: '100%',
          borderCollapse: 'collapse',
          fontSize: '12px',
          fontFamily: 'Inter, sans-serif',
        }}
      >
        {/* Header */}
        <thead>
          <tr>
            {columns.map(col => (
              <th
                key={col.key}
                onClick={() => col.sortable && handleSort(col.key)}
                style={{
                  textAlign: 'left',
                  padding: '8px 16px',
                  backgroundColor: 'var(--color-primary)',
                  color: '#fff',
                  fontWeight: 500,
                  fontSize: '11px',
                  textTransform: 'uppercase',
                  letterSpacing: '0.4px',
                  cursor: col.sortable ? 'pointer' : 'default',
                  userSelect: 'none',
                  width: col.width,
                  whiteSpace: 'nowrap',
                }}
              >
                {col.label}
                {col.sortable && (
                  <span style={{ opacity: 0.7, fontSize: '10px' }}>
                    {sortIcon(col.key)}
                  </span>
                )}
              </th>
            ))}
          </tr>
        </thead>

        {/* Body */}
        <tbody>
          {isLoading
            ? [0, 1, 2].map(i => (
                <tr key={i}>
                  {columns.map(col => (
                    <td key={col.key} style={{ padding: '8px 16px', borderBottom: '1px solid var(--color-border)' }}>
                      <div
                        style={{
                          height: '14px',
                          borderRadius: '4px',
                          backgroundColor: 'var(--color-neutral-light)',
                          animation: 'pulse 1.5s ease-in-out infinite',
                        }}
                      />
                    </td>
                  ))}
                </tr>
              ))
            : data.map((row, rowIndex) => (
                <tr key={rowIndex}>
                  {columns.map(col => (
                    <td
                      key={col.key}
                      style={{
                        padding: '8px 16px',
                        borderBottom: '1px solid var(--color-border)',
                        backgroundColor: rowIndex % 2 === 1 ? 'var(--color-row-alt)' : 'var(--color-surface)',
                        color: 'var(--color-neutral-dark)',
                      }}
                    >
                      {String(row[col.key] ?? '')}
                    </td>
                  ))}
                </tr>
              ))}
        </tbody>
      </table>

      {/* Pagination */}
      {pagination && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            gap: '12px',
            padding: '8px 16px',
            borderTop: '1px solid var(--color-border)',
            fontSize: '11px',
            color: 'var(--color-neutral-dark)',
          }}
        >
          <span>
            Showing {start}–{end} of {pagination.total}
          </span>
          <button
            onClick={() => pagination.onPageChange(pagination.page - 1)}
            disabled={pagination.page <= 1}
            style={{
              padding: '4px 12px',
              fontSize: '11px',
              fontWeight: 600,
              border: '1px solid var(--color-border)',
              borderRadius: '4px',
              backgroundColor: pagination.page <= 1 ? 'var(--color-neutral-light)' : 'var(--color-surface)',
              color: pagination.page <= 1 ? '#aaa' : 'var(--color-primary)',
              cursor: pagination.page <= 1 ? 'not-allowed' : 'pointer',
            }}
          >
            ← Prev
          </button>
          <button
            onClick={() => pagination.onPageChange(pagination.page + 1)}
            disabled={end >= pagination.total}
            style={{
              padding: '4px 12px',
              fontSize: '11px',
              fontWeight: 600,
              border: '1px solid var(--color-border)',
              borderRadius: '4px',
              backgroundColor: end >= pagination.total ? 'var(--color-neutral-light)' : 'var(--color-primary)',
              color: end >= pagination.total ? '#aaa' : '#fff',
              cursor: end >= pagination.total ? 'not-allowed' : 'pointer',
            }}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
