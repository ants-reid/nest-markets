"use client";

import { useMemo, useState } from "react";
import styles from "./DataTable.module.css";

type CellValue = string | number | boolean | null | undefined;

type RowData = Record<string, any>;

export interface DataTableColumn<T extends RowData = RowData> {
  key: keyof T & string;
  label: string;
  sortable?: boolean;
  align?: "left" | "center" | "right";
  width?: string;
  render?: (value: T[keyof T], row: T) => React.ReactNode;
}

type SortDir = "asc" | "desc";

interface SortState {
  key: string;
  dir: SortDir;
}

interface DataTableProps<T extends RowData = RowData> {
  columns: DataTableColumn<T>[];
  data: T[];
  searchable?: boolean;
  pageSize?: number;
  loading?: boolean;
  emptyMessage?: string;
  className?: string;
  rowKey?: (row: T, index: number) => string;
}

function sortRows<T extends RowData>(rows: T[], sort: SortState): T[] {
  return [...rows].sort((a, b) => {
    const av = a[sort.key] ?? "";
    const bv = b[sort.key] ?? "";
    if (typeof av === "number" && typeof bv === "number") {
      return sort.dir === "asc" ? av - bv : bv - av;
    }
    const as = String(av).toLowerCase();
    const bs = String(bv).toLowerCase();
    const cmp = as < bs ? -1 : as > bs ? 1 : 0;
    return sort.dir === "asc" ? cmp : -cmp;
  });
}

function filterRows<T extends RowData>(rows: T[], query: string, columns: DataTableColumn<T>[]): T[] {
  const q = query.trim().toLowerCase();
  if (!q) return rows;
  return rows.filter((row) =>
    columns.some((col) => {
      const v = row[col.key];
      return v != null && String(v).toLowerCase().includes(q);
    })
  );
}

export function DataTable<T extends RowData = RowData>({
  columns,
  data,
  searchable = false,
  pageSize,
  loading = false,
  emptyMessage = "No data",
  className,
  rowKey,
}: DataTableProps<T>) {
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<SortState | null>(null);
  const [page, setPage] = useState(0);

  const filtered = useMemo(() => filterRows(data, query, columns), [data, query, columns]);
  const sorted = useMemo(() => (sort ? sortRows(filtered, sort) : filtered), [filtered, sort]);

  const totalPages = pageSize ? Math.max(1, Math.ceil(sorted.length / pageSize)) : 1;
  const safePage = Math.min(page, totalPages - 1);
  const paginated = pageSize ? sorted.slice(safePage * pageSize, (safePage + 1) * pageSize) : sorted;

  function toggleSort(key: string) {
    setPage(0);
    setSort((prev) => {
      if (!prev || prev.key !== key) return { key, dir: "asc" };
      if (prev.dir === "asc") return { key, dir: "desc" };
      return null;
    });
  }

  function handleSearch(value: string) {
    setQuery(value);
    setPage(0);
  }

  const showToolbar = searchable;

  return (
    <div className={[styles.wrapper, className].filter(Boolean).join(" ")}>
      {showToolbar && (
        <div className={styles.toolbar}>
          {searchable && (
            <div className={styles.searchWrap}>
              <span className={styles.searchIcon} aria-hidden="true">⌕</span>
              <input
                type="search"
                placeholder="Search…"
                value={query}
                onChange={(e) => handleSearch(e.target.value)}
                className={styles.searchInput}
                aria-label="Search table"
              />
            </div>
          )}
          <div className={styles.toolbarRight}>
            {query && (
              <span className={styles.rowCount}>
                {filtered.length} of {data.length} rows
              </span>
            )}
            {!query && (
              <span className={styles.rowCount}>{data.length} rows</span>
            )}
          </div>
        </div>
      )}

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead className={styles.thead}>
            <tr>
              {columns.map((col) => {
                const isActive = sort?.key === col.key;
                const thClass = [
                  styles.th,
                  col.align === "right" ? styles.right : col.align === "center" ? styles.center : "",
                  col.sortable ? styles.sortable : "",
                  isActive ? styles.sortActive : "",
                ]
                  .filter(Boolean)
                  .join(" ");
                return (
                  <th
                    key={col.key}
                    className={thClass}
                    style={col.width ? { width: col.width } : undefined}
                    onClick={col.sortable ? () => toggleSort(col.key) : undefined}
                    aria-sort={
                      isActive ? (sort?.dir === "asc" ? "ascending" : "descending") : undefined
                    }
                  >
                    {col.label}
                    {col.sortable && (
                      <span className={styles.sortIcon} aria-hidden="true">
                        {isActive ? (sort?.dir === "asc" ? "↑" : "↓") : "⇅"}
                      </span>
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={columns.length} className={styles.stateRow}>
                  <div className={styles.loadingRow}>Loading…</div>
                </td>
              </tr>
            ) : paginated.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className={styles.stateRow}>
                  <div className={styles.emptyRow}>{emptyMessage}</div>
                </td>
              </tr>
            ) : (
              paginated.map((row, i) => (
                <tr
                  key={rowKey ? rowKey(row, i) : i}
                  className={styles.tr}
                >
                  {columns.map((col) => {
                    const tdClass = [
                      styles.td,
                      col.align === "right" ? styles.right : col.align === "center" ? styles.center : "",
                    ]
                      .filter(Boolean)
                      .join(" ");
                    return (
                      <td key={col.key} className={tdClass}>
                        {col.render ? col.render(row[col.key], row) : (row[col.key] ?? "—")}
                      </td>
                    );
                  })}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {pageSize && totalPages > 1 && (
        <div className={styles.pagination}>
          <span className={styles.paginationInfo}>
            Showing {safePage * pageSize + 1}–{Math.min((safePage + 1) * pageSize, sorted.length)} of {sorted.length}
          </span>
          <div className={styles.paginationControls}>
            <button
              className={styles.pageBtn}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={safePage === 0}
              aria-label="Previous page"
            >
              ‹
            </button>
            {Array.from({ length: Math.min(totalPages, 7) }, (_, idx) => {
              const startPage = Math.max(0, safePage - 3);
              const pg = startPage + idx;
              if (pg >= totalPages) return null;
              return (
                <button
                  key={pg}
                  className={[styles.pageBtn, pg === safePage ? styles.pageBtnActive : ""].filter(Boolean).join(" ")}
                  onClick={() => setPage(pg)}
                  aria-current={pg === safePage ? "page" : undefined}
                >
                  {pg + 1}
                </button>
              );
            })}
            <button
              className={styles.pageBtn}
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={safePage >= totalPages - 1}
              aria-label="Next page"
            >
              ›
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
