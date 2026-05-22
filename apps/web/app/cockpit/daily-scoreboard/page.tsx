"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { EmptyState } from "../../../components/ui/EmptyState";
import {
  getCockpitDailyScoreboard,
  type CockpitDailyScoreboardContributor,
  type CockpitDailyScoreboardDayStatus,
  type CockpitDailyScoreboardResponse,
} from "../../../lib/api/cockpitDailyScoreboard";
import styles from "../../../styles/pages/cockpit-daily-scoreboard.module.css";

function formatTimestamp(value: string | null): string {
  if (!value) return "unknown";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

function formatDate(value: string): string {
  const d = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function formatCurrency(value: number | null): string {
  if (value === null) return "unknown";
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);
}

function pnlClass(value: number | null): string {
  if (value === null) return styles.pnlUnknown;
  if (value > 0) return styles.pnlPositive;
  if (value < 0) return styles.pnlNegative;
  return styles.pnlFlat;
}

function dayStatusClass(value: CockpitDailyScoreboardDayStatus): string {
  if (value === "green_day") return styles.statusGreen;
  if (value === "red_day") return styles.statusRed;
  if (value === "flat_day") return styles.statusFlat;
  if (value === "monitor_attention") return styles.statusMonitor;
  if (value === "review_required") return styles.statusReview;
  if (value === "data_incomplete") return styles.statusIncomplete;
  return styles.statusUnknown;
}

function severityClass(value: string): string {
  const normalized = value.toLowerCase();
  if (normalized === "critical" || normalized === "error") return styles.severityDanger;
  if (normalized === "warn" || normalized === "warning") return styles.severityWarn;
  return styles.severityInfo;
}

function isEmpty(report: CockpitDailyScoreboardResponse): boolean {
  return (
    report.summary.trades_opened_today === 0 &&
    report.summary.trades_closed_today === 0 &&
    report.summary.open_positions_now === 0 &&
    report.risk_and_monitor_notes.length === 0
  );
}

function ContributorRow({ item }: { item: CockpitDailyScoreboardContributor }) {
  return (
    <div className={styles.contributorRow}>
      <span className={styles.contributorSymbol}>{item.symbol}</span>
      <span className={`${styles.contributorPnl} ${pnlClass(item.realized_pnl)}`}>
        {formatCurrency(item.realized_pnl)}
      </span>
      <span className={styles.contributorLabel}>{item.contribution_label}</span>
    </div>
  );
}

export default function CockpitDailyScoreboardPage() {
  const [report, setReport] = useState<CockpitDailyScoreboardResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getCockpitDailyScoreboard();
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

  return (
    <main className={styles.page} data-testid="cockpit-daily-scoreboard-page">
      <div className={styles.container}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>Daily Scoreboard</h1>
            <p className={styles.subtitle}>
              Read-only daily paper-trading scoreboard covering performance, activity, risk context,
              and review priorities for the next operator session.
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

        <div className={styles.paperBanner} data-testid="cockpit-daily-paper-mode">
          <strong>Paper mode only.</strong> This surface is strictly read-only and cannot place,
          close, modify, or approve trades.
        </div>

        {error ? (
          <EmptyState
            variant="error"
            title="Daily scoreboard unavailable"
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
            title="Loading daily scoreboard…"
            message="Pulling read-only daily paper metrics from the cockpit API."
          />
        ) : null}

        {report ? (
          <>
            <section className={styles.heroCard}>
              <div>
                <p className={styles.eyebrow}>Scoreboard date</p>
                <h2 className={styles.heroTitle}>{formatDate(report.report_date)}</h2>
                <p className={styles.heroSubtitle}>{report.summary.headline}</p>
              </div>
              <div className={styles.heroMeta}>
                <span className={styles.modePill}>{report.mode}</span>
                <span className={`${styles.dayStatusPill} ${dayStatusClass(report.summary.day_status)}`}>
                  {report.summary.day_status.replaceAll("_", " ")}
                </span>
                <span className={styles.generatedAt}>Generated {formatTimestamp(report.generated_at)}</span>
              </div>
            </section>

            <section className={styles.summaryGrid} data-testid="cockpit-daily-summary-cards">
              <article className={styles.summaryCard}>
                <span className={styles.summaryLabel}>Trades opened today</span>
                <span className={styles.summaryValue}>{report.summary.trades_opened_today}</span>
              </article>
              <article className={styles.summaryCard}>
                <span className={styles.summaryLabel}>Trades closed today</span>
                <span className={styles.summaryValue}>{report.summary.trades_closed_today}</span>
              </article>
              <article className={styles.summaryCard}>
                <span className={styles.summaryLabel}>Open positions now</span>
                <span className={styles.summaryValue}>{report.summary.open_positions_now}</span>
              </article>
              <article className={styles.summaryCard}>
                <span className={styles.summaryLabel}>Realized P&amp;L today</span>
                <span className={`${styles.summaryValue} ${pnlClass(report.performance.realized_pnl_today)}`}>
                  {formatCurrency(report.performance.realized_pnl_today)}
                </span>
              </article>
              <article className={styles.summaryCard}>
                <span className={styles.summaryLabel}>Unrealized snapshot</span>
                <span className={`${styles.summaryValue} ${pnlClass(report.performance.unrealized_pnl_snapshot)}`}>
                  {formatCurrency(report.performance.unrealized_pnl_snapshot)}
                </span>
              </article>
              <article className={styles.summaryCard}>
                <span className={styles.summaryLabel}>Net P&amp;L today</span>
                <span className={`${styles.summaryValue} ${pnlClass(report.performance.net_pnl_today)}`}>
                  {formatCurrency(report.performance.net_pnl_today)}
                </span>
              </article>
            </section>

            {isEmpty(report) ? (
              <EmptyState
                title="No paper scoreboard activity yet"
                message="Daily scoreboard activity is currently empty because no paper trades or attention notes were recorded for this day."
              />
            ) : null}

            <section className={styles.twoCol}>
              <article className={styles.sectionCard}>
                <h2 className={styles.sectionTitle}>Performance panel</h2>
                <div className={styles.metricGrid}>
                  <div className={styles.metricCard}>
                    <span className={styles.metricLabel}>Win / loss / flat</span>
                    <span className={styles.metricValue}>
                      {report.performance.win_count ?? "?"} / {report.performance.loss_count ?? "?"} / {report.performance.flat_count ?? "?"}
                    </span>
                    <span className={styles.metricMeta}>Unknown closes: {report.performance.unknown_count}</span>
                  </div>
                  <div className={styles.metricCard}>
                    <span className={styles.metricLabel}>Day status</span>
                    <span className={`${styles.metricValue} ${dayStatusClass(report.summary.day_status)}`}>
                      {report.summary.day_status.replaceAll("_", " ")}
                    </span>
                  </div>
                </div>
              </article>

              <article className={styles.sectionCard}>
                <h2 className={styles.sectionTitle}>Activity panel</h2>
                <div className={styles.metricGrid}>
                  <div className={styles.metricCard}>
                    <span className={styles.metricLabel}>Opened today</span>
                    <span className={styles.metricValue}>{report.activity.trades_opened_today}</span>
                  </div>
                  <div className={styles.metricCard}>
                    <span className={styles.metricLabel}>Closed today</span>
                    <span className={styles.metricValue}>{report.activity.trades_closed_today}</span>
                  </div>
                  <div className={styles.metricCard}>
                    <span className={styles.metricLabel}>Open positions now</span>
                    <span className={styles.metricValue}>{report.activity.open_positions_now}</span>
                  </div>
                </div>
              </article>
            </section>

            <section className={styles.twoCol}>
              <article className={styles.sectionCard}>
                <h2 className={styles.sectionTitle}>Open positions panel</h2>
                <div className={styles.metricGrid}>
                  <div className={styles.metricCard}>
                    <span className={styles.metricLabel}>Total open positions</span>
                    <span className={styles.metricValue}>{report.open_positions.count}</span>
                  </div>
                  <div className={styles.metricCard}>
                    <span className={styles.metricLabel}>Long count</span>
                    <span className={styles.metricValue}>{report.open_positions.long_count}</span>
                  </div>
                  <div className={styles.metricCard}>
                    <span className={styles.metricLabel}>Short count</span>
                    <span className={styles.metricValue}>{report.open_positions.short_count}</span>
                  </div>
                </div>
              </article>

              <article className={styles.sectionCard}>
                <h2 className={styles.sectionTitle}>Closed positions panel</h2>
                <div className={styles.metricGrid}>
                  <div className={styles.metricCard}>
                    <span className={styles.metricLabel}>Closed count</span>
                    <span className={styles.metricValue}>{report.closed_positions.count}</span>
                  </div>
                  <div className={styles.metricCard}>
                    <span className={styles.metricLabel}>Wins / losses / flat</span>
                    <span className={styles.metricValue}>
                      {report.closed_positions.wins ?? "?"} / {report.closed_positions.losses ?? "?"} / {report.closed_positions.flat ?? "?"}
                    </span>
                    <span className={styles.metricMeta}>Unknown: {report.closed_positions.unknown}</span>
                  </div>
                </div>
              </article>
            </section>

            <section className={styles.sectionCard} data-testid="cockpit-daily-top-contributors">
              <h2 className={styles.sectionTitle}>Top contributors panel</h2>
              {report.top_contributors.items.length === 0 ? (
                <p className={styles.emptyText}>Top contributors are unavailable for this day.</p>
              ) : (
                <div className={styles.contributorList}>
                  {report.top_contributors.items.map((item) => (
                    <ContributorRow key={`${item.symbol}-${item.contribution_label}`} item={item} />
                  ))}
                </div>
              )}
            </section>

            <section className={styles.twoCol} data-testid="cockpit-daily-notes-panels">
              <article className={styles.sectionCard}>
                <h2 className={styles.sectionTitle}>Risk and monitor notes</h2>
                {report.risk_and_monitor_notes.length === 0 ? (
                  <p className={styles.emptyText}>No risk or monitor notes were reported for this day.</p>
                ) : (
                  <ul className={styles.noteList}>
                    {report.risk_and_monitor_notes.map((note, index) => (
                      <li key={`${note.title}-${index}`} className={styles.noteItem}>
                        <div className={styles.noteHeader}>
                          <strong>{note.title}</strong>
                          <span className={`${styles.severityPill} ${severityClass(note.severity)}`}>
                            {note.severity}
                          </span>
                        </div>
                        <p>{note.detail}</p>
                        <small>
                          {note.label.replaceAll("_", " ")} · {formatTimestamp(note.created_at)}
                        </small>
                      </li>
                    ))}
                  </ul>
                )}
              </article>

              <article className={styles.sectionCard}>
                <h2 className={styles.sectionTitle}>Review priorities</h2>
                <ul className={styles.noteList}>
                  {report.review_priorities.map((entry, index) => (
                    <li key={`priority-${index}`} className={styles.noteItem}>{entry}</li>
                  ))}
                </ul>
              </article>
            </section>

            <section className={styles.sectionCard}>
              <h2 className={styles.sectionTitle}>Limitations and missing data</h2>
              {report.limitations.length === 0 ? (
                <p className={styles.emptyText}>No explicit limitations were reported.</p>
              ) : (
                <ul className={styles.noteList}>
                  {report.limitations.map((entry, index) => (
                    <li key={`limitation-${index}`} className={styles.noteItem}>{entry}</li>
                  ))}
                </ul>
              )}
            </section>
          </>
        ) : null}
      </div>
    </main>
  );
}
