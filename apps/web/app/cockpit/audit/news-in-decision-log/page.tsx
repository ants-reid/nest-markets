"use client";

// MH-NEWS-08-A2-UI — Read-only cockpit tile for news-in-decision audit log.
//
// Renders /news-in-decision-log/recent (MH-NEWS-08-A2). The table is empty
// until the future MH-NEWS-08-B writer is wired (paired with MH-NEWS-04);
// the page surfaces the API's advisory note and shows a friendly empty
// state until then.
//
// Drift-lock guarantee: pure read-only frontend. Does not call any
// trading, broker, worker, news-ingestion, or risk-mutation endpoint.

import { useCallback, useEffect, useState } from "react";

import {
  getRecentNewsInDecisionLog,
  type NewsInDecisionLogResponse,
  type NewsInDecisionLogRow,
} from "../../../../lib/api/newsInDecisionLog";
import styles from "../../../../styles/pages/cockpit-audit-news-in-decision-log.module.css";

const LIMIT_OPTIONS = [25, 50, 100, 200];
const KIND_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
  { value: "", label: "any kind" },
  { value: "signal_generation", label: "signal_generation" },
  { value: "risk_review", label: "risk_review" },
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

function Row({ row }: { row: NewsInDecisionLogRow }) {
  return (
    <tr className={styles.row}>
      <td className={styles.cellTime} title={formatTimestamp(row.created_at)}>
        {formatTimestamp(row.created_at)}
      </td>
      <td className={styles.cellKind}>{row.decision_kind}</td>
      <td className={styles.cellMono} title={row.signal_id ?? ""}>
        {shortId(row.signal_id)}
      </td>
      <td className={styles.cellMono} title={row.news_article_id ?? ""}>
        {shortId(row.news_article_id)}
      </td>
      <td>
        <span className={styles.badgeResearchOnly}>{row.evidence_class}</span>
      </td>
      <td
        className={styles.cellHeadline}
        title={row.headline_snapshot ?? ""}
      >
        {row.headline_snapshot ?? "—"}
      </td>
      <td className={styles.cellMono}>{row.source_snapshot ?? "—"}</td>
    </tr>
  );
}

export default function NewsInDecisionLogAuditPage() {
  const [snapshot, setSnapshot] =
    useState<NewsInDecisionLogResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  const [limit, setLimit] = useState<number>(25);
  const [decisionKind, setDecisionKind] = useState<string>("");
  const [signalId, setSignalId] = useState<string>("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await getRecentNewsInDecisionLog({
        limit,
        decisionKind: decisionKind || null,
        signalId: signalId || null,
      });
      setSnapshot(resp);
      setLastRefreshed(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [limit, decisionKind, signalId]);

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
            <h1 className={styles.title}>News-in-Decision Audit Log</h1>
            <p className={styles.subtitle}>
              Read-only audit log of news items consumed by future decision
              pipelines. The underlying table is empty until the
              MH-NEWS-08-B writer is wired (paired with MH-NEWS-04). This
              page never modifies state.
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

          <label className={styles.filterLabel} htmlFor="kind">
            Decision kind
          </label>
          <select
            id="kind"
            className={styles.filterSelect}
            value={decisionKind}
            onChange={(e) => setDecisionKind(e.target.value)}
          >
            {KIND_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

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
          Drift lock: this page is strictly read-only. No request issued
          here can modify any decision, news record, or trading state, and
          the underlying audit row evidence_class is locked to
          <code> research_only</code> at the database layer.
        </div>

        {error && <div className={styles.errorBanner}>{error}</div>}

        {!error && items.length === 0 && !loading ? (
          <div className={styles.empty}>
            No news-in-decision audit rows recorded yet. The MH-NEWS-08-B
            writer is not wired in this cycle, so the table is expected to
            be empty.
          </div>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Created</th>
                  <th>Kind</th>
                  <th>Signal</th>
                  <th>Article</th>
                  <th>Evidence</th>
                  <th>Headline</th>
                  <th>Source</th>
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
