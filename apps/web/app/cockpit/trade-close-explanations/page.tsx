"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AssetContextLink } from "../../../components/ui/AssetContextLink";
import { EmptyState } from "../../../components/ui/EmptyState";
import {
  getCockpitTradeCloseExplanations,
  type CockpitTradeCloseExplanation,
  type CockpitTradeCloseExplanationsResponse,
} from "../../../lib/api/cockpitTradeCloseExplanations";
import styles from "../../../styles/pages/cockpit-trade-close-explanations.module.css";

function formatTimestamp(value: string | null): string {
  if (!value) return "unknown";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

function prettyLabel(value: string): string {
  return value.replaceAll("_", " ");
}

function pnlClass(value: number | null): string {
  if (value === null) return styles.pnlUnknown;
  if (value > 0) return styles.pnlPositive;
  if (value < 0) return styles.pnlNegative;
  return styles.pnlFlat;
}

function labelClass(value: CockpitTradeCloseExplanation["close_label"]): string {
  if (value === "target_hit") return styles.labelTarget;
  if (value === "stop_hit") return styles.labelStop;
  if (value === "risk_close") return styles.labelRisk;
  if (value === "timeout_or_stale") return styles.labelTimeout;
  if (value === "validation_close") return styles.labelValidation;
  if (value === "manual_close") return styles.labelManual;
  return styles.labelUnknown;
}

function outcomeClass(value: CockpitTradeCloseExplanation["outcome_match"]): string {
  if (value === "matched") return styles.outcomeMatched;
  if (value === "mismatched") return styles.outcomeMismatched;
  return styles.outcomeUnknown;
}

function isEmpty(report: CockpitTradeCloseExplanationsResponse): boolean {
  return report.summary.total_closed_trades === 0;
}

export default function CockpitTradeCloseExplanationsPage() {
  const [report, setReport] = useState<CockpitTradeCloseExplanationsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getCockpitTradeCloseExplanations();
      setReport(response);
      setLastRefreshed(new Date());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : String(loadError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const explanations = useMemo(() => {
    if (!report) return [];
    return [...report.explanations].sort((a, b) => {
      const timeA = a.closed_at ?? "";
      const timeB = b.closed_at ?? "";
      return timeB.localeCompare(timeA);
    });
  }, [report]);

  return (
    <main className={styles.page} data-testid="cockpit-trade-close-explanations-page">
      <div className={styles.container}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>Trade-Close Explanations</h1>
            <p className={styles.subtitle}>
              Read-focused explanations for recently closed paper trades, including close-label inference,
              evidence, missing context, and learning notes.
            </p>
          </div>
          <div className={styles.headerActions}>
            <Link href="/cockpit" className={styles.linkPill}>
              ← Cockpit hub
            </Link>
            {lastRefreshed ? (
              <span className={styles.refreshTimestamp}>Updated {lastRefreshed.toLocaleTimeString()}</span>
            ) : null}
            <button type="button" className={styles.refreshButton} onClick={() => void load()} disabled={loading}>
              {loading ? "Loading…" : "Refresh"}
            </button>
          </div>
        </header>

        <div className={styles.paperBanner} data-testid="cockpit-trade-close-paper-mode">
          <strong>Paper mode only.</strong> This page is strictly read-only and does not place, close,
          modify, or execute trades.
        </div>

        {error ? (
          <EmptyState
            variant="error"
            title="Trade-close explanations unavailable"
            message={error}
            action={
              <button type="button" className={styles.retryButton} onClick={() => void load()}>
                Retry
              </button>
            }
          />
        ) : null}

        {!error && loading && !report ? (
          <EmptyState
            variant="loading"
            title="Loading trade-close explanations…"
            message="Pulling read-only close reasoning from the cockpit API."
          />
        ) : null}

        {report ? (
          <>
            <section className={styles.heroCard}>
              <div>
                <p className={styles.eyebrow}>Generated</p>
                <h2 className={styles.heroTitle}>{formatTimestamp(report.generated_at)}</h2>
                <p className={styles.heroSubtitle}>{report.summary.headline}</p>
              </div>
              <div className={styles.heroMeta}>
                <span className={styles.modePill}>{report.mode}</span>
                <span className={styles.metaNote}>All explanations are non-actionable audit context.</span>
              </div>
            </section>

            <section className={styles.summaryGrid} data-testid="cockpit-trade-close-summary-cards">
              <article className={styles.summaryCard}>
                <span className={styles.summaryLabel}>Closed trades</span>
                <span className={styles.summaryValue}>{report.summary.total_closed_trades}</span>
              </article>
              <article className={styles.summaryCard}>
                <span className={styles.summaryLabel}>Known close labels</span>
                <span className={styles.summaryValue}>{report.summary.known_close_labels}</span>
              </article>
              <article className={styles.summaryCard}>
                <span className={styles.summaryLabel}>Unknown close labels</span>
                <span className={styles.summaryValue}>{report.summary.unknown_close_labels}</span>
              </article>
              <article className={styles.summaryCard}>
                <span className={styles.summaryLabel}>Profitable</span>
                <span className={styles.summaryValue}>{report.summary.profitable_trades}</span>
              </article>
              <article className={styles.summaryCard}>
                <span className={styles.summaryLabel}>Losing</span>
                <span className={styles.summaryValue}>{report.summary.losing_trades}</span>
              </article>
              <article className={styles.summaryCard}>
                <span className={styles.summaryLabel}>Setup matched</span>
                <span className={styles.summaryValue}>{report.summary.setup_matched}</span>
              </article>
            </section>

            {isEmpty(report) ? (
              <EmptyState
                title="No closed paper trades yet"
                message="No closed paper positions were found, so trade-close explanations are currently empty."
              />
            ) : null}

            <section className={styles.sectionCard}>
              <h2 className={styles.sectionTitle}>Recently closed trades</h2>
              <p className={styles.sectionSubtitle}>Read-only close explanations sorted by most recent close time.</p>

              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Symbol</th>
                      <th>Closed</th>
                      <th>Label</th>
                      <th>Status</th>
                      <th>P&amp;L</th>
                      <th>Setup match</th>
                    </tr>
                  </thead>
                  <tbody>
                    {explanations.map((item) => (
                      <tr key={item.id}>
                        <td>{item.symbol}</td>
                        <td>{formatTimestamp(item.closed_at)}</td>
                        <td>
                          <span className={`${styles.labelPill} ${labelClass(item.close_label)}`}>
                            {prettyLabel(item.close_label)}
                          </span>
                        </td>
                        <td>{item.status}</td>
                        <td className={pnlClass(item.realized_pnl)}>
                          {item.realized_pnl === null ? "unknown" : item.realized_pnl.toFixed(2)}
                        </td>
                        <td>
                          <span className={`${styles.outcomePill} ${outcomeClass(item.outcome_match)}`}>
                            {item.outcome_match}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className={styles.detailGrid} data-testid="cockpit-trade-close-explanation-list">
              {explanations.map((item) => (
                <article key={`detail-${item.id}`} className={styles.detailCard}>
                  <div className={styles.detailHeader}>
                    <h3 className={styles.detailTitle}>{item.symbol}</h3>
                    <span className={`${styles.labelPill} ${labelClass(item.close_label)}`}>
                      {prettyLabel(item.close_label)}
                    </span>
                  </div>

                  <p className={styles.detailSummary}>{item.result_summary}</p>
                  <div className={styles.assetContextRow}>
                    <AssetContextLink context={item} fallbackSymbol={item.symbol} />
                  </div>

                  <div className={styles.detailMeta}>
                    <span><strong>Opened:</strong> {formatTimestamp(item.opened_at)}</span>
                    <span><strong>Closed:</strong> {formatTimestamp(item.closed_at)}</span>
                    <span><strong>Status:</strong> {item.status}</span>
                    <span><strong>Close reason:</strong> {item.close_reason ?? "unknown"}</span>
                    <span><strong>Position id:</strong> {item.position_id ?? "unknown"}</span>
                    <span><strong>Paper order id:</strong> {item.paper_order_id ?? "unknown"}</span>
                    <span><strong>Actionable:</strong> {item.is_actionable ? "yes" : "no"}</span>
                  </div>

                  <div className={styles.inlineSection}>
                    <h4>Evidence</h4>
                    {item.evidence.length === 0 ? <p className={styles.emptyText}>No evidence provided.</p> : null}
                    <ul>
                      {item.evidence.map((entry) => (
                        <li key={`${item.id}-ev-${entry}`}>{entry}</li>
                      ))}
                    </ul>
                  </div>

                  <div className={styles.inlineSection}>
                    <h4>Missing data</h4>
                    {item.missing_data.length === 0 ? <p className={styles.emptyText}>None flagged.</p> : null}
                    <ul>
                      {item.missing_data.map((entry) => (
                        <li key={`${item.id}-md-${entry}`}>{entry}</li>
                      ))}
                    </ul>
                  </div>

                  <div className={styles.inlineSection}>
                    <h4>Learning note</h4>
                    <p>{item.learning_note}</p>
                  </div>
                </article>
              ))}
            </section>

            <section className={styles.twoCol}>
              <article className={styles.sectionCard}>
                <h2 className={styles.sectionTitle}>Recommended review actions</h2>
                <ul className={styles.noteList}>
                  {report.recommended_review_actions.map((entry, index) => (
                    <li key={`action-${index}`} className={styles.noteItem}>{entry}</li>
                  ))}
                </ul>
              </article>

              <article className={styles.sectionCard}>
                <h2 className={styles.sectionTitle}>Limitations</h2>
                {report.limitations.length === 0 ? <p className={styles.emptyText}>No explicit limitations were reported.</p> : null}
                <ul className={styles.noteList}>
                  {report.limitations.map((entry, index) => (
                    <li key={`limitation-${index}`} className={styles.noteItem}>{entry}</li>
                  ))}
                </ul>
              </article>
            </section>
          </>
        ) : null}
      </div>
    </main>
  );
}
