"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { EmptyState } from "../../../components/ui/EmptyState";
import {
  getCockpitInFlightAdjustments,
  type CockpitInFlightAdjustmentsResponse,
  type CockpitInFlightItem,
} from "../../../lib/api/cockpitInFlightAdjustments";
import styles from "../../../styles/pages/cockpit-in-flight-adjustments.module.css";

function formatTimestamp(value: string | null): string {
  if (!value) return "unknown";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

function severityClass(value: string): string {
  const normalized = value.toLowerCase();
  if (normalized === "critical" || normalized === "error") return styles.severityCritical;
  if (normalized === "warn" || normalized === "warning") return styles.severityWarning;
  if (normalized === "info") return styles.severityInfo;
  return styles.severityUnknown;
}

function attentionClass(value: CockpitInFlightItem["attention_level"]): string {
  if (value === "high") return styles.attentionHigh;
  if (value === "medium") return styles.attentionMedium;
  if (value === "low") return styles.attentionLow;
  return styles.attentionUnknown;
}

function labelClass(value: CockpitInFlightItem["adjustment_label"]): string {
  if (value === "risk_attention") return styles.labelRisk;
  if (value === "review_required") return styles.labelReview;
  if (value === "stale_data") return styles.labelStale;
  if (value === "missing_context") return styles.labelMissing;
  if (value === "monitor_issue") return styles.labelMonitor;
  if (value === "watch_only") return styles.labelWatch;
  return styles.labelUnknown;
}

function prettyLabel(value: string): string {
  return value.replaceAll("_", " ");
}

function isEmptyReport(report: CockpitInFlightAdjustmentsResponse): boolean {
  return report.summary.total_items === 0;
}

export default function CockpitInFlightAdjustmentsPage() {
  const [report, setReport] = useState<CockpitInFlightAdjustmentsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getCockpitInFlightAdjustments();
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

  const sortedItems = useMemo(() => {
    if (!report) return [];
    return [...report.items].sort((a, b) => {
      const rank = (value: string) => {
        if (value === "high") return 3;
        if (value === "medium") return 2;
        if (value === "low") return 1;
        return 0;
      };
      const byAttention = rank(b.attention_level) - rank(a.attention_level);
      if (byAttention !== 0) return byAttention;
      const aTime = a.created_at ?? a.opened_at ?? "";
      const bTime = b.created_at ?? b.opened_at ?? "";
      return bTime.localeCompare(aTime);
    });
  }, [report]);

  return (
    <main className={styles.page} data-testid="cockpit-in-flight-adjustments-page">
      <div className={styles.container}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>In-Flight Adjustments</h1>
            <p className={styles.subtitle}>
              Read-focused paper-mode visibility for open paper positions, active paper orders,
              and active paper recommendations that may need operator review.
            </p>
          </div>
          <div className={styles.headerActions}>
            <Link href="/cockpit" className={styles.linkPill}>
              ← Cockpit hub
            </Link>
            {lastRefreshed ? (
              <span className={styles.refreshTimestamp}>
                Updated {lastRefreshed.toLocaleTimeString()}
              </span>
            ) : null}
            <button type="button" className={styles.refreshButton} onClick={() => void load()} disabled={loading}>
              {loading ? "Loading…" : "Refresh"}
            </button>
          </div>
        </header>

        <div className={styles.paperBanner} data-testid="cockpit-in-flight-paper-mode">
          <strong>Paper mode only.</strong> This page is strictly read-only and cannot place,
          close, cancel, or modify trades.
        </div>

        {error ? (
          <EmptyState
            variant="error"
            title="In-flight adjustments unavailable"
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
            title="Loading in-flight adjustments…"
            message="Pulling read-only paper-mode adjustment visibility from the cockpit API."
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
                <span className={styles.modeMeta}>All items are non-actionable visibility records.</span>
              </div>
            </section>

            <section className={styles.summaryGrid} data-testid="cockpit-in-flight-summary-cards">
              <article className={styles.summaryCard}>
                <span className={styles.summaryLabel}>In-flight items</span>
                <span className={styles.summaryValue}>{report.summary.total_items}</span>
              </article>
              <article className={styles.summaryCard}>
                <span className={styles.summaryLabel}>Open paper positions</span>
                <span className={styles.summaryValue}>{report.summary.open_positions}</span>
              </article>
              <article className={styles.summaryCard}>
                <span className={styles.summaryLabel}>Open paper orders</span>
                <span className={styles.summaryValue}>{report.summary.open_orders}</span>
              </article>
              <article className={styles.summaryCard}>
                <span className={styles.summaryLabel}>Active recommendations</span>
                <span className={styles.summaryValue}>{report.summary.active_recommendations}</span>
              </article>
              <article className={styles.summaryCard}>
                <span className={styles.summaryLabel}>Review required</span>
                <span className={styles.summaryValue}>{report.summary.review_required}</span>
              </article>
              <article className={styles.summaryCard}>
                <span className={styles.summaryLabel}>High attention</span>
                <span className={styles.summaryValue}>{report.summary.high_attention}</span>
              </article>
            </section>

            {isEmptyReport(report) ? (
              <EmptyState
                title="No in-flight paper items yet"
                message="No open paper positions, active paper orders, or active recommendations were found in persisted data."
              />
            ) : null}

            <section className={styles.sectionCard}>
              <h2 className={styles.sectionTitle}>Attention list</h2>
              <p className={styles.sectionSubtitle}>
                Items are sorted by attention level and remain read-only. Recommended review actions are advisory only.
              </p>

              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Type</th>
                      <th>Symbol</th>
                      <th>Status</th>
                      <th>Label</th>
                      <th>Attention</th>
                      <th>Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedItems.map((item) => (
                      <tr key={item.id}>
                        <td>{prettyLabel(item.item_type)}</td>
                        <td>{item.symbol}</td>
                        <td>{item.status}</td>
                        <td>
                          <span className={`${styles.labelPill} ${labelClass(item.adjustment_label)}`}>
                            {prettyLabel(item.adjustment_label)}
                          </span>
                        </td>
                        <td>
                          <span className={`${styles.attentionPill} ${attentionClass(item.attention_level)}`}>
                            {item.attention_level}
                          </span>
                        </td>
                        <td>{formatTimestamp(item.created_at ?? item.opened_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className={styles.detailGrid} data-testid="cockpit-in-flight-item-list">
              {sortedItems.map((item) => (
                <article key={`detail-${item.id}`} className={styles.detailCard}>
                  <div className={styles.detailHeader}>
                    <h3 className={styles.detailTitle}>{item.symbol}</h3>
                    <span className={`${styles.attentionPill} ${attentionClass(item.attention_level)}`}>
                      {item.attention_level}
                    </span>
                  </div>
                  <p className={styles.detailType}>{prettyLabel(item.item_type)} • {item.status}</p>
                  <p className={styles.detailSummary}>{item.current_state_summary}</p>
                  <p className={styles.detailReason}>{item.reason}</p>

                  <div className={styles.detailMeta}>
                    <span>
                      <strong>Opened:</strong> {formatTimestamp(item.opened_at)}
                    </span>
                    <span>
                      <strong>Created:</strong> {formatTimestamp(item.created_at)}
                    </span>
                    <span>
                      <strong>Label:</strong> {prettyLabel(item.adjustment_label)}
                    </span>
                    <span>
                      <strong>Actionable:</strong> {item.is_actionable ? "yes" : "no"}
                    </span>
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
                    <h4>Recommended review action</h4>
                    <p>{item.recommended_review_action}</p>
                  </div>
                </article>
              ))}
            </section>

            <section className={styles.twoCol}>
              <article className={styles.sectionCard}>
                <h2 className={styles.sectionTitle}>Monitor notes</h2>
                {report.monitor_notes.length === 0 ? <p className={styles.emptyText}>No monitor notes in this snapshot.</p> : null}
                <ul className={styles.noteList}>
                  {report.monitor_notes.map((note, index) => (
                    <li key={`${note.title}-${index}`} className={styles.noteItem}>
                      <div className={styles.noteHeader}>
                        <strong>{note.title}</strong>
                        <span className={`${styles.severityPill} ${severityClass(note.severity)}`}>
                          {note.severity}
                        </span>
                      </div>
                      <p>{note.detail}</p>
                      <small>{formatTimestamp(note.created_at)}</small>
                    </li>
                  ))}
                </ul>
              </article>

              <article className={styles.sectionCard}>
                <h2 className={styles.sectionTitle}>Risk notes</h2>
                <ul className={styles.noteList}>
                  {report.risk_notes.map((note, index) => (
                    <li key={`risk-${index}`} className={styles.noteItem}>
                      {note}
                    </li>
                  ))}
                </ul>
              </article>
            </section>

            <section className={styles.twoCol}>
              <article className={styles.sectionCard}>
                <h2 className={styles.sectionTitle}>Recommended review actions</h2>
                <ul className={styles.noteList}>
                  {report.recommended_review_actions.map((entry, index) => (
                    <li key={`action-${index}`} className={styles.noteItem}>
                      {entry}
                    </li>
                  ))}
                </ul>
              </article>

              <article className={styles.sectionCard}>
                <h2 className={styles.sectionTitle}>Limitations</h2>
                {report.limitations.length === 0 ? <p className={styles.emptyText}>No explicit limitations were reported.</p> : null}
                <ul className={styles.noteList}>
                  {report.limitations.map((entry, index) => (
                    <li key={`limitation-${index}`} className={styles.noteItem}>
                      {entry}
                    </li>
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
