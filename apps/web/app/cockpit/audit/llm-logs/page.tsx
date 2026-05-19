"use client";

// MH-COCKPIT-AUDIT-A-LLM-LOG — Read-only cockpit tile for LLM round-trips.
//
// Renders /llm-logs/recent (MH-COCKPIT-04-API). Previews are already
// redacted at the API layer; this page does not echo raw secrets.
//
// Drift-lock guarantee: pure read-only frontend. Does not call any LLM
// provider, does not call any trading, broker, worker, or
// risk-mutation endpoint.

import { useCallback, useEffect, useState } from "react";

import {
  getRecentLLMLogs,
  type LLMLogItem,
  type LLMLogsResponse,
} from "../../../../lib/api/llmLogs";
import styles from "../../../../styles/pages/cockpit-audit-llm-logs.module.css";

const LIMIT_OPTIONS = [25, 50, 100, 200];

function formatTimestamp(value: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

function shortText(value: string | null, max: number): string {
  if (!value) return "—";
  return value.length > max ? `${value.slice(0, max)}…` : value;
}

function Row({ row }: { row: LLMLogItem }) {
  const isError = row.error_class != null;
  return (
    <tr className={styles.row}>
      <td className={styles.cellTime} title={formatTimestamp(row.created_at)}>
        {formatTimestamp(row.created_at)}
      </td>
      <td className={styles.cellMono}>{row.provider ?? "—"}</td>
      <td className={styles.cellMono}>
        {row.model_returned ?? row.model_requested ?? "—"}
      </td>
      <td className={styles.cellNum}>{row.latency_ms ?? "—"}</td>
      <td className={styles.cellNum}>{row.total_tokens ?? "—"}</td>
      <td>
        <span
          className={isError ? styles.badgeError : styles.badgeOk}
          title={row.stop_reason ?? ""}
        >
          {isError ? row.error_class : (row.stop_reason ?? "ok")}
        </span>
      </td>
      <td
        className={styles.cellPreview}
        title={row.user_prompt_preview ?? ""}
      >
        {shortText(row.user_prompt_preview, 120)}
      </td>
      <td className={styles.cellMono} title={row.correlation_id ?? ""}>
        {shortText(row.correlation_id, 12)}
      </td>
    </tr>
  );
}

export default function LlmLogsAuditPage() {
  const [snapshot, setSnapshot] = useState<LLMLogsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  const [limit, setLimit] = useState<number>(25);
  const [provider, setProvider] = useState<string>("");
  const [correlationId, setCorrelationId] = useState<string>("");
  const [onlyErrors, setOnlyErrors] = useState<boolean>(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await getRecentLLMLogs({
        limit,
        provider: provider || undefined,
        correlationId: correlationId || undefined,
        onlyErrors,
      });
      setSnapshot(resp);
      setLastRefreshed(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [limit, provider, correlationId, onlyErrors]);

  useEffect(() => {
    void load();
    // Initial load only; subsequent refreshes are user-driven.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const items = snapshot?.items ?? [];

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>LLM Logs Audit</h1>
            <p className={styles.subtitle}>
              Read-only audit view of redacted LLM round-trips
              (MH-150). Previews are length-capped and control-stripped
              at write time. This page never invokes any LLM provider
              and never modifies state.
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

          <label className={styles.filterLabel} htmlFor="provider">
            Provider
          </label>
          <input
            id="provider"
            className={styles.filterInput}
            value={provider}
            placeholder="optional (e.g. openai)"
            onChange={(e) => setProvider(e.target.value.trim())}
          />

          <label className={styles.filterLabel} htmlFor="correlation">
            Correlation id
          </label>
          <input
            id="correlation"
            className={styles.filterInput}
            value={correlationId}
            placeholder="optional"
            onChange={(e) => setCorrelationId(e.target.value.trim())}
          />

          <label className={styles.filterCheckLabel}>
            <input
              type="checkbox"
              checked={onlyErrors}
              onChange={(e) => setOnlyErrors(e.target.checked)}
            />
            Errors only
          </label>
        </section>

        <div className={styles.driftLockNotice}>
          Drift lock: this page is strictly read-only. No request from
          this page invokes an LLM provider or modifies any trading
          state, signal, or risk decision.
        </div>

        {error && <div className={styles.errorBanner}>{error}</div>}

        {!error && items.length === 0 && !loading ? (
          <div className={styles.empty}>
            No LLM log rows match the current filters.
          </div>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Created</th>
                  <th>Provider</th>
                  <th>Model</th>
                  <th>Latency (ms)</th>
                  <th>Tokens</th>
                  <th>Status</th>
                  <th>User prompt preview</th>
                  <th>Correlation</th>
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
