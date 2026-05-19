"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { deactivateAsset, getAssets, type AssetListResponse, type AssetResponse } from "../../lib/api";
import { useLivePolling } from "../../lib/hooks/useLivePolling";
import { PageShell } from "../../components/ui/PageShell";
import { PageHeader } from "../../components/shell/PageHeader";
import { DataTable, type DataTableColumn } from "../../components/ui/DataTable";
import { StatusChip, statusVariantFor } from "../../components/ui/StatusChip";
import { EmptyState } from "../../components/ui/EmptyState";
import { Button } from "../../components/ui/Button";

const ASSET_CLASS_LABELS: Record<string, string> = {
  fx: "FX",
  equity: "Equity",
  etf: "ETF",
  index_proxy: "Index Proxy",
  commodity_proxy: "Commodity",
  crypto: "Crypto",
};

type AssetRow = AssetResponse & { _deactivating: boolean };

function buildColumns(
  onDeactivate: (a: AssetResponse) => void,
): DataTableColumn<AssetRow>[] {
  return [
    {
      key: "symbol",
      label: "Symbol",
      sortable: true,
      width: "100px",
      render: (v, row) => (
        <Link
          href={`/signals?asset=${encodeURIComponent(String(v))}`}
          style={{ color: "var(--accent-primary)", fontWeight: 700, textDecoration: "none" }}
        >
          {String(v)}
        </Link>
      ),
    },
    { key: "name", label: "Name", sortable: true },
    {
      key: "asset_class",
      label: "Class",
      sortable: true,
      width: "120px",
      render: (v) => (
        <span style={{
          display: "inline-block",
          padding: "2px 8px",
          borderRadius: 6,
          border: "1px solid var(--surface-border)",
          background: "var(--surface-soft)",
          fontSize: 11,
          fontWeight: 700,
          letterSpacing: "0.04em",
          color: "var(--text-muted)",
          textTransform: "uppercase",
        }}>
          {ASSET_CLASS_LABELS[String(v)] ?? String(v)}
        </span>
      ),
    },
    { key: "base_currency", label: "Base", sortable: true, width: "70px" },
    { key: "quote_currency", label: "Quote", sortable: true, width: "70px" },
    { key: "exchange", label: "Exchange", sortable: true, width: "100px" },
    {
      key: "is_active",
      label: "Status",
      sortable: true,
      width: "90px",
      render: (v) => (
        <StatusChip
          variant={v ? "success" : "muted"}
          label={v ? "Active" : "Inactive"}
        />
      ),
    },
    {
      key: "id",
      label: "",
      width: "100px",
      align: "right",
      render: (_v, row) =>
        row.is_active ? (
          <Button
            variant="ghost"
            size="sm"
            disabled={row._deactivating}
            onClick={() => onDeactivate(row)}
          >
            {row._deactivating ? "…" : "Deactivate"}
          </Button>
        ) : null,
    },
  ];
}

export default function AssetsPage() {
  const [data, setData] = useState<AssetListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [deactivating, setDeactivating] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const result = await getAssets({ active_only: false });
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load assets.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  useLivePolling(() => load(), 20000, { enabled: true, runImmediately: false });

  async function handleDeactivate(asset: AssetResponse) {
    if (!confirm(`Deactivate ${asset.symbol}?`)) return;
    setDeactivating(asset.id);
    try {
      await deactivateAsset(asset.id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to deactivate.");
    } finally {
      setDeactivating(null);
    }
  }

  const rows: AssetRow[] =
    data?.items.map((a) => ({ ...a, _deactivating: deactivating === a.id })) ?? [];

  const columns = buildColumns(handleDeactivate);

  const activeCount = rows.filter((r) => r.is_active).length;
  const inactiveCount = rows.length - activeCount;

  return (
    <PageShell>
      <PageHeader
        title="Asset Universe"
        subtitle="Instruments monitored by the signal sweep worker."
        actions={
          data ? (
            <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
              {data.total} instrument{data.total !== 1 ? "s" : ""}
            </span>
          ) : undefined
        }
      />

      {/* KPI strip */}
      {data && (
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          {[
            { label: "Total", value: String(rows.length) },
            { label: "Active", value: String(activeCount), color: "var(--state-success)" },
            { label: "Inactive", value: String(inactiveCount), color: "var(--text-muted)" },
          ].map((kpi) => (
            <div
              key={kpi.label}
              style={{
                padding: "10px 16px",
                border: "1px solid var(--surface-border)",
                borderRadius: 12,
                background: "var(--surface-fill)",
                display: "flex",
                flexDirection: "column",
                gap: 2,
                minWidth: 80,
              }}
            >
              <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: "var(--text-muted)" }}>
                {kpi.label}
              </span>
              <span style={{ fontSize: 24, fontWeight: 700, color: kpi.color ?? "var(--text-strong)", lineHeight: 1.1 }}>
                {kpi.value}
              </span>
            </div>
          ))}
        </div>
      )}

      {loading && <EmptyState variant="loading" title="Loading assets…" />}

      {error && <EmptyState variant="error" message={error} />}

      {!loading && data && (
        <DataTable<AssetRow>
          columns={columns}
          data={rows}
          searchable
          rowKey={(r) => r.id}
          emptyMessage="No assets found."
        />
      )}
    </PageShell>
  );
}
