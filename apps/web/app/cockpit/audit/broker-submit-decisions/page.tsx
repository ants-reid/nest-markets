"use client";

// MH-148-B-UI — Read-only cockpit tile for broker-submit decisions audit log.
//
// Renders the most recent rows from /broker/submit-decisions/recent
// (MH-148-B). The table is empty until the future MH-148-C writer is wired
// (paired with MH-147); the page surfaces the advisory note from the API
// and shows a friendly empty state until then.
//
// Drift-lock guarantee: pure read-only frontend. Does not call any
// trading, broker, worker, or risk-mutation endpoint. Auto-paper enforcement,
// auto trading, and live trading remain OFF.

import { useCallback, useEffect, useState } from "react";

import {
  getRecentBrokerSubmitDecisions,
  type BrokerSubmitDecisionRow,
  type BrokerSubmitDecisionsResponse,
} from "../../../../lib/api/brokerSubmitDecisions";
import styles from "../../../../styles/pages/cockpit-audit-broker-submit-decisions.module.css";

const LIMIT_OPTIONS = [25, 50, 100, 200];
const INTENT_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
  { value: "", label: "any intent" },
  { value: "auto", label: "auto" },
  { value: "manual", label: "manual" },
  { value: "paper", label: "paper" },
];
const BLOCK_OPTIONS: ReadonlyArray<{
  value: "any" | "blocked" | "passed";
  label: string;
}> = [
  { value: "any", label: "any outcome" },
  { value: "blocked", label: "would-block" },
  { value: "passed", label: "passed preflight" },
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

function DecisionRow({ row }: { row: BrokerSubmitDecisionRow }) {
  return (
    <tr className={styles.row}>
      <td className={styles.cellTime} title={formatTimestamp(row.created_at)}>
        {formatTimestamp(row.created_at)}
      </td>
      <td className={styles.cellMono} title={row.signal_id ?? ""}>
        {shortId(row.signal_id)}
      </td>
      <td className={styles.cellIntent}>{row.intent}</td>
      <td>
        <span
          className={
            row.would_block ? styles.badgeBlocked : styles.badgePassed
          }
        >
          {row.would_block ? "would-block" : "passed"}
        </span>
      </td>
      <td className={styles.cellMono}>{row.blocked_reason_code ?? "—"}</td>
      <td
        className={styles.cellReason}
        title={row.blocked_reason_text ?? ""}
      >
        {row.blocked_reason_text ?? "—"}
      </td>
    </tr>
  );
}

export default function BrokerSubmitDecisionsAuditPage() {
  const [snapshot, setSnapshot] =
    useState<BrokerSubmitDecisionsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  const [limit, setLimit] = useState<number>(25);
  const [intent, setIntent] = useState<string>("");
  const [blockFilter, setBlockFilter] = useState<"any" | "blocked" | "passed">(
    "any",
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const wouldBlock =
        blockFilter === "any" ? null : blockFilter === "blocked";
      const resp = await getRecentBrokerSubmitDecisions({
        limit,
        intent: intent || null,
        wouldBlock,
      });
      setSnapshot(resp);
      setLastRefreshed(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [limit, intent, blockFilter]);

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
            <h1 className={styles.title}>Broker Submit Decisions (audit)</h1>
            <p className={styles.subtitle}>
              Read-only audit log of broker-submit preflight decisions. The
              underlying table is empty until the MH-148-C writer is wired
              (paired with MH-147). This page never modifies state.
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

          <label className={styles.filterLabel} htmlFor="intent">
            Intent
          </label>
          <select
            id="intent"
            className={styles.filterSelect}
            value={intent}
            onChange={(e) => setIntent(e.target.value)}
          >
            {INTENT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          <label className={styles.filterLabel} htmlFor="block">
            Outcome
          </label>
          <select
            id="block"
            className={styles.filterSelect}
            value={blockFilter}
            onChange={(e) =>
              setBlockFilter(e.target.value as "any" | "blocked" | "passed")
            }
          >
            {BLOCK_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </section>

        {advisory && <div className={styles.advisory}>{advisory}</div>}

        <div className={styles.driftLockNotice}>
          Drift lock: this page is strictly read-only. No request issued from
          here can submit, cancel, or modify any broker order, and it does not
          relax auto-paper / auto-trading / live-trading enforcement.
        </div>

        {error && <div className={styles.errorBanner}>{error}</div>}

        {!error && items.length === 0 && !loading ? (
          <div className={styles.empty}>
            No broker-submit decisions recorded yet. The MH-148-C writer is
            not wired in this cycle, so the table is expected to be empty.
          </div>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Created</th>
                  <th>Signal</th>
                  <th>Intent</th>
                  <th>Outcome</th>
                  <th>Reason code</th>
                  <th>Reason text</th>
                </tr>
              </thead>
              <tbody>
                {items.map((row) => (
                  <DecisionRow key={row.id} row={row} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  );
}
