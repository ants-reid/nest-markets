"use client";

// MH-RISK-AUDIT-A-UI — Read-only cockpit tile for risk_decisions audit.
//
// Renders /risk-decisions/recent (MH-RISK-AUDIT-A). Unlike the other
// audit tiles in this bucket, the underlying table is already populated
// by the deterministic risk evaluator, so the table generally contains
// real rows. Filters: limit, approved-status, block_reason_code marker,
// signal id (UUID).
//
// Drift-lock guarantee: pure read-only frontend. Does not call any
// trading, broker, worker, news-ingestion, or risk-mutation endpoint.

import { useCallback, useEffect, useState } from "react";

import {
  getRecentRiskDecisions,
  type RiskDecisionRow,
  type RiskDecisionsResponse,
} from "../../../../lib/api/riskDecisions";
import styles from "../../../../styles/pages/cockpit-audit-risk-decisions.module.css";

const LIMIT_OPTIONS = [25, 50, 100, 200];
const APPROVED_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
  { value: "", label: "any status" },
  { value: "approved", label: "approved" },
  { value: "blocked", label: "blocked" },
  { value: "pending", label: "pending" },
];

function formatTimestamp(value: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

function shortId(value: string | null): string {
  if (!value) return "—";
  return value.length > 8 ? `${value.slice(0, 8)}…` : value;
}

function approvedClass(approved: string): string {
  if (approved === "approved") return styles.badgeApproved;
  if (approved === "blocked") return styles.badgeBlocked;
  return styles.badgePending;
}

function Row({ row }: { row: RiskDecisionRow }) {
  return (
    <tr className={styles.row}>
      <td className={styles.cellTime} title={formatTimestamp(row.created_at)}>
        {formatTimestamp(row.created_at)}
      </td>
      <td>
        <span className={approvedClass(row.approved)}>{row.approved}</span>
      </td>
      <td className={styles.cellMono} title={row.signal_id ?? ""}>
        {shortId(row.signal_id)}
      </td>
      <td className={styles.cellMono} title={row.risk_profile_id ?? ""}>
        {shortId(row.risk_profile_id)}
      </td>
      <td className={styles.cellRule} title={row.blocking_rule ?? ""}>
        {row.blocking_rule ?? "—"}
      </td>
      <td className={styles.cellMono}>{row.block_reason_code ?? "—"}</td>
    </tr>
  );
}

export default function RiskDecisionsAuditPage() {
  const [snapshot, setSnapshot] = useState<RiskDecisionsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  const [limit, setLimit] = useState<number>(25);
  const [approved, setApproved] = useState<string>("");
  const [blockReasonCode, setBlockReasonCode] = useState<string>("");
  const [signalId, setSignalId] = useState<string>("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await getRecentRiskDecisions({
        limit,
        approved: approved || null,
        signalId: signalId || null,
        blockReasonCode: blockReasonCode || null,
      });
      setSnapshot(resp);
      setLastRefreshed(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [limit, approved, signalId, blockReasonCode]);

  useEffect(() => {
    void load();
    // Initial load only; subsequent refreshes are user-driven.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const items = snapshot?.items ?? [];
  const advisory = snapshot?.advisory ?? null;

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>Risk Decisions Audit</h1>
            <p className={styles.subtitle}>
              Read-only audit view of the deterministic risk-engine decision
              table. Source: <code>risk_service.RiskEvaluator</code> and
              <code> persistence_signal_service</code>. This page never
              modifies state.
            </p>
          </div>
          <div className={styles.headerActions}>
            <button
              type="button"
              className={styles.refreshButton}
              onClick={() => {
                void load();
              }}
              disabled={loading}
            >
              {loading ? "Refreshing…" : "Refresh"}
            </button>
            {lastRefreshed && (
              <span className={styles.refreshTimestamp}>
                refreshed {lastRefreshed.toLocaleTimeString()}
              </span>
            )}
          </div>
        </header>

        <section className={styles.filters}>
          <label className={styles.filterLabel} htmlFor="limit">
            Limit
          </label>
          <select
            id="limit"
            className={styles.filterSelect}
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
          >
            {LIMIT_OPTIONS.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>

          <label className={styles.filterLabel} htmlFor="approved">
            Approved
          </label>
          <select
            id="approved"
            className={styles.filterSelect}
            value={approved}
            onChange={(e) => setApproved(e.target.value)}
          >
            {APPROVED_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          <label className={styles.filterLabel} htmlFor="reason">
            Block reason code
          </label>
          <input
            id="reason"
            className={styles.filterInput}
            value={blockReasonCode}
            placeholder="optional code (e.g. SPREAD_EXCEEDED)"
            onChange={(e) => setBlockReasonCode(e.target.value.trim())}
          />

          <label className={styles.filterLabel} htmlFor="signal">
            Signal id
          </label>
          <input
            id="signal"
            className={styles.filterInput}
            value={signalId}
            placeholder="optional UUID"
            onChange={(e) => setSignalId(e.target.value.trim())}
          />
        </section>

        {advisory && <div className={styles.advisory}>{advisory}</div>}

        <div className={styles.driftLockNotice}>
          Drift lock: this page is strictly read-only. The deterministic
          risk evaluator and the gate state in
          <code> trading_control_service</code> are not modified by any
          request issued from this page.
        </div>

        {error && <div className={styles.errorBanner}>{error}</div>}

        {!error && items.length === 0 && !loading ? (
          <div className={styles.empty}>
            No risk-decision rows match the current filters.
          </div>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Created</th>
                  <th>Approved</th>
                  <th>Signal</th>
                  <th>Risk Profile</th>
                  <th>Blocking Rule</th>
                  <th>Reason Code</th>
                </tr>
              </thead>
              <tbody>
                {items.map((row) => (
                  <Row key={row.id} row={row} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  );
}
