"use client";

// MH-COCKPIT-13-B — Auto-paper status card page (read-only).
// Renders /cockpit/auto-paper/status. Surfaces drift-lock posture only;
// no toggles, no enable buttons, no broker actions.

import { useCallback, useEffect, useState } from "react";

import {
  getAutoPaperStatusCard,
  type AutoPaperStatusCard,
  type AutoPaperStatusPosture,
} from "../../../lib/api/cockpitAutoPaperStatus";
import styles from "../../../styles/pages/auto-paper-status.module.css";

const POSTURE_COLOR: Record<AutoPaperStatusPosture, string> = {
  ok: "var(--state-success)",
  warning: "var(--state-warning)",
  blocked: "var(--state-danger)",
};

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

interface ChipProps {
  label: string;
  on: boolean;
  // When `on` is true, render as alarming (red); when false, as safe (green).
}

function EnforcementChip({ label, on }: ChipProps) {
  return (
    <span className={`${styles.chip} ${on ? styles.chipOn : styles.chipOff}`}>
      {label}: {on ? "ON" : "OFF"}
    </span>
  );
}

export default function AutoPaperStatusPage() {
  const [card, setCard] = useState<AutoPaperStatusCard | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await getAutoPaperStatusCard();
      setCard(resp);
      setLastRefreshed(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const postureClass = card ? styles[card.posture] ?? "" : "";
  const postureColor = card ? POSTURE_COLOR[card.posture] : "var(--text-muted)";

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>Auto-Paper Status</h1>
            <p className={styles.subtitle}>
              Read-only posture for the auto-paper subsystem. This card does
              not enable, arm, or modify any trading control. Auto-paper
              enforcement, auto trading, and live trading remain OFF.
            </p>
          </div>
          <div style={{ display: "grid", gap: "0.4rem", justifyItems: "end" }}>
            {lastRefreshed && (
              <span className={styles.refreshTimestamp}>
                Updated {lastRefreshed.toLocaleTimeString()}
              </span>
            )}
            <button
              type="button"
              className={styles.refreshButton}
              onClick={() => void load()}
              disabled={loading}
            >
              {loading ? "Loading…" : "Refresh"}
            </button>
          </div>
        </header>

        {error && <div className={styles.errorBanner}>Failed to load: {error}</div>}

        {card && <div className={styles.advisory}>{card.advisory}</div>}

        {!card && loading && <div className={styles.loading}>Loading status card…</div>}

        {card && (
          <section className={`${styles.card} ${postureClass}`}>
            <div className={styles.cardHeader}>
              <div className={styles.postureRow}>
                <span
                  className={styles.posturePill}
                  style={{ color: postureColor }}
                >
                  {card.posture}
                </span>
                <span className={styles.code}>
                  trading mode: {card.trading_control.trading_mode} / arming:{" "}
                  {card.trading_control.arming_state}
                </span>
              </div>
              <h2 className={styles.headline}>{card.headline}</h2>
              <p className={styles.subline}>{card.subline}</p>
            </div>

            <div className={styles.chipRow}>
              <EnforcementChip
                label="Auto-paper enforcement"
                on={card.enforcement.auto_paper_enforcement_enabled}
              />
              <EnforcementChip
                label="Auto trading"
                on={card.enforcement.auto_trading_enabled}
              />
              <EnforcementChip
                label="Live trading"
                on={card.enforcement.live_trading_enabled}
              />
              <EnforcementChip
                label="Live submission"
                on={card.enforcement.live_order_submission_allowed}
              />
            </div>

            <div className={styles.metaGrid}>
              <div className={styles.metaItem}>
                <span className={styles.metaLabel}>Paper submission</span>
                <span className={styles.metaValue}>
                  {card.trading_control.paper_order_submission_allowed
                    ? "allowed"
                    : "blocked"}
                </span>
              </div>
              <div className={styles.metaItem}>
                <span className={styles.metaLabel}>Execution control</span>
                <span className={styles.metaValue}>
                  {card.trading_control.execution_control}
                </span>
              </div>
              <div className={styles.metaItem}>
                <span className={styles.metaLabel}>Emergency stop</span>
                <span className={styles.metaValue}>
                  {card.trading_control.emergency_stop_active
                    ? "active"
                    : "clear"}
                </span>
              </div>
              <div className={styles.metaItem}>
                <span className={styles.metaLabel}>Run-log entries</span>
                <span className={styles.metaValue}>
                  {card.run_log_summary.current_entry_count} /{" "}
                  {card.run_log_summary.max_entries}
                </span>
              </div>
              <div className={styles.metaItem}>
                <span className={styles.metaLabel}>Run-log utilization</span>
                <span className={styles.metaValue}>
                  {card.run_log_summary.utilization_pct.toFixed(1)}%
                </span>
              </div>
              <div className={styles.metaItem}>
                <span className={styles.metaLabel}>Latest run</span>
                <span className={styles.metaValue}>
                  {formatTimestamp(card.run_log_summary.latest_started_at)}
                </span>
              </div>
            </div>

            {card.trading_control.reasons.length > 0 && (
              <div className={styles.section}>
                <h3 className={styles.sectionTitle}>Trading-control notes</h3>
                <ul className={styles.linkList}>
                  {card.trading_control.reasons.map((r, idx) => (
                    <li key={`r-${idx}`} className={styles.code}>
                      {r}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {card.latest_run && (
              <div className={styles.section}>
                <h3 className={styles.sectionTitle}>Latest worker run</h3>
                <div className={styles.metaGrid}>
                  <div className={styles.metaItem}>
                    <span className={styles.metaLabel}>Worker</span>
                    <span className={styles.metaValue}>
                      {card.latest_run.worker_name}
                    </span>
                  </div>
                  <div className={styles.metaItem}>
                    <span className={styles.metaLabel}>Status</span>
                    <span className={styles.metaValue}>
                      {card.latest_run.status}
                    </span>
                  </div>
                  <div className={styles.metaItem}>
                    <span className={styles.metaLabel}>Source</span>
                    <span className={styles.metaValue}>
                      {card.latest_run.source}
                    </span>
                  </div>
                  <div className={styles.metaItem}>
                    <span className={styles.metaLabel}>Started</span>
                    <span className={styles.metaValue}>
                      {formatTimestamp(card.latest_run.started_at)}
                    </span>
                  </div>
                </div>
                <div className={styles.code}>{card.latest_run.message}</div>
              </div>
            )}

            <div className={styles.section}>
              <h3 className={styles.sectionTitle}>Related read-only routes</h3>
              <ul className={styles.linkList}>
                {Object.entries(card.links).map(([label, path]) => (
                  <li key={label} className={styles.linkRow}>
                    <span className={styles.linkLabel}>{label}</span>
                    <span className={styles.linkPath}>{path}</span>
                  </li>
                ))}
              </ul>
            </div>
          </section>
        )}

        <div className={styles.driftLockNotice}>
          Drift lock active: this view is read-only. Auto-paper enforcement,
          auto trading, and live trading remain OFF. Nothing on this page can
          submit orders or change a gate.
        </div>
      </div>
    </main>
  );
}
