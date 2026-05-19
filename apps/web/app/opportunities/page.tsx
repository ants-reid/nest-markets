"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { getOpportunities, runSweep, type OpportunityListResponse, type RankedOpportunity } from "../../lib/api";
import { useLivePolling } from "../../lib/hooks/useLivePolling";
import { PageShell } from "../../components/ui/PageShell";
import { PageHeader } from "../../components/shell/PageHeader";
import { DataTable, type DataTableColumn } from "../../components/ui/DataTable";
import { StatusChip } from "../../components/ui/StatusChip";
import { EmptyState } from "../../components/ui/EmptyState";
import { Button } from "../../components/ui/Button";

function ScoreBar({ score }: { score: number }) {
  const max = 100;
  const pct = Math.min(100, (score / max) * 100);
  const color = score >= 75 ? "var(--state-success)" : score >= 55 ? "var(--state-warning)" : "var(--state-danger)";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, minWidth: 90 }}>
      <div style={{ flex: 1, height: 5, borderRadius: 3, background: "var(--chart-track-bg)", overflow: "hidden" }}>
        <div style={{ width: `${pct.toFixed(1)}%`, height: "100%", background: color, borderRadius: 3 }} />
      </div>
      <span style={{ color, fontWeight: 700, fontSize: 12, minWidth: 28, textAlign: "right" as const }}>{score}</span>
    </div>
  );
}

const COLUMNS: DataTableColumn<RankedOpportunity>[] = [
  {
    key: "asset",
    label: "Asset",
    sortable: true,
    width: "90px",
    render: (v) => (
      <Link href={`/signals?asset=${encodeURIComponent(String(v))}`} style={{ color: "var(--accent-primary)", fontWeight: 700, textDecoration: "none" }}>
        {String(v)}
      </Link>
    ),
  },
  { key: "asset_class", label: "Class", sortable: true, width: "100px" },
  {
    key: "direction",
    label: "Direction",
    sortable: true,
    width: "90px",
    render: (v) => (
      <StatusChip
        variant={v === "long" ? "success" : v === "short" ? "danger" : "muted"}
        label={String(v).toUpperCase()}
      />
    ),
  },
  { key: "setup_type", label: "Setup", sortable: true },
  {
    key: "confidence",
    label: "Confidence",
    sortable: true,
    align: "right",
    width: "100px",
    render: (v) => `${((Number(v) ?? 0) * 100).toFixed(0)}%`,
  },
  {
    key: "score",
    label: "Score",
    sortable: true,
    width: "120px",
    render: (v) => <ScoreBar score={Number(v) ?? 0} />,
  },
  {
    key: "entry_low",
    label: "Entry Range",
    width: "140px",
    render: (v, row) => (
      <Link href={`/risk?asset=${encodeURIComponent(row.asset)}`} style={{ color: "var(--text-body)", textDecoration: "none" }}>
        {row.entry_low} – {row.entry_high}
      </Link>
    ),
  },
  { key: "stop_price", label: "Stop", sortable: true, align: "right", width: "80px" },
  { key: "target_price", label: "Target", sortable: true, align: "right", width: "80px" },
  { key: "regime", label: "Regime", sortable: true, width: "90px" },
];

export default function OpportunitiesPage() {
  const [data, setData] = useState<OpportunityListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [sweeping, setSweeping] = useState(false);
  const [sweepMsg, setSweepMsg] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const result = await getOpportunities(50);
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load opportunities.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  useLivePolling(() => load(), 15000, { enabled: true, runImmediately: false });

  async function handleRunSweep() {
    setSweeping(true);
    setSweepMsg(null);
    try {
      const result = await runSweep();
      setSweepMsg(result.status === "ok" ? `Sweep complete — ${result.message}` : `Sweep error: ${result.message}`);
      void load();
    } catch (e) {
      setSweepMsg(e instanceof Error ? e.message : "Sweep failed.");
    } finally {
      setSweeping(false);
    }
  }

  const longCount = data?.items.filter((i) => i.direction === "long").length ?? 0;
  const shortCount = data?.items.filter((i) => i.direction === "short").length ?? 0;
  const topScore = data?.items[0]?.score ?? null;

  return (
    <PageShell width="xl">
      <PageHeader
        title="Ranked Opportunities"
        subtitle="Top-ranked trade setups from the latest signal sweep, sorted by score."
        actions={
          <>
            <Button variant="primary" size="sm" loading={sweeping} onClick={() => void handleRunSweep()}>
              {sweeping ? "Running sweep…" : "Run Sweep Now"}
            </Button>
            <Button variant="secondary" size="sm" onClick={() => void load()}>
              Refresh
            </Button>
          </>
        }
      />

      {sweepMsg && (
        <div style={{
          padding: "10px 14px",
          borderRadius: 10,
          border: `1px solid ${sweepMsg.startsWith("Sweep error") ? "var(--state-danger-border)" : "var(--state-success-border)"}`,
          background: sweepMsg.startsWith("Sweep error") ? "var(--state-danger-soft)" : "var(--state-success-soft)",
          color: sweepMsg.startsWith("Sweep error") ? "var(--state-danger)" : "var(--state-success)",
          fontSize: 13,
        }}>
          {sweepMsg}
        </div>
      )}

      {/* KPI strip */}
      {data && (
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          {[
            { label: "Total", value: String(data.items.length) },
            { label: "Long", value: String(longCount), color: "var(--state-success)" },
            { label: "Short", value: String(shortCount), color: "var(--state-danger)" },
            ...(topScore !== null ? [{ label: "Top Score", value: String(topScore), color: "var(--accent-highlight)" }] : []),
          ].map((kpi) => (
            <div key={kpi.label} style={{ padding: "10px 16px", border: "1px solid var(--surface-border)", borderRadius: 12, background: "var(--surface-fill)", minWidth: 80, display: "flex", flexDirection: "column", gap: 2 }}>
              <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: "var(--text-muted)" }}>{kpi.label}</span>
              <span style={{ fontSize: 24, fontWeight: 700, color: kpi.color ?? "var(--text-strong)", lineHeight: 1.1 }}>{kpi.value}</span>
            </div>
          ))}
        </div>
      )}

      {loading && <EmptyState variant="loading" title="Loading opportunities…" />}
      {error && <EmptyState variant="error" message={error} />}

      {!loading && data && (
        <DataTable<RankedOpportunity>
          columns={COLUMNS}
          data={data.items}
          searchable
          rowKey={(r) => r.signal_id}
          emptyMessage="No ranked opportunities yet. Run a sweep to populate."
        />
      )}
    </PageShell>
  );
}
