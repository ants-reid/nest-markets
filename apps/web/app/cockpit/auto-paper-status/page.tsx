"use client";

// MH-COCKPIT-13-B — Auto-paper status card page (read-only).
// Renders /cockpit/auto-paper-status. Surfaces drift-lock posture only;
// no toggles, no enable buttons, no broker actions.

import { useCallback, useEffect, useState } from "react";

import {
  getAutoPaperStatusCard,
  type AutoPaperStatusCard,
  type AutoPaperStatusPosture,
  type AutoPaperStatusRiskGateItem,
} from "../../../lib/api/cockpitAutoPaperStatus";
import styles from "../../../styles/pages/auto-paper-status.module.css";

const POSTURE_CLASS: Record<AutoPaperStatusPosture, string> = {
  ok: styles.postureOk,
  warning: styles.postureWarning,
  blocked: styles.postureBlocked,
};

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return Number.isInteger(value) ? `${value}` : value.toFixed(2);
}

interface ChipProps {
  label: string;
  on: boolean;
}

function EnforcementChip({ label, on }: ChipProps) {
  return (
    <span className={`${styles.chip} ${on ? styles.chipOn : styles.chipOff}`}>
      {label}: {on ? "ON" : "OFF"}
    </span>
  );
}

function GateItem({ item }: { item: AutoPaperStatusRiskGateItem }) {
  return (
    <div className={styles.gateItem} data-status={item.status}>
      <div className={styles.gateHeaderRow}>
        <span className={styles.gateLabel}>{item.label}</span>
        <span className={styles.gateStatus}>{item.status}</span>
      </div>
      <p className={styles.gateDetail}>{item.detail}</p>
    </div>
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
  const posturePillClass = card ? POSTURE_CLASS[card.posture] : "";

  return (
    <main className={styles.page} data-testid="auto-paper-status-page">
      <div className={styles.container}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>Auto-Paper Status</h1>
            <p className={styles.subtitle}>
              Read-only posture for the Auto Paper subsystem. This page is for
              operator visibility only and cannot enable, arm, or modify any
              trading control.
            </p>
          </div>
          <div className={styles.refreshPanel}>
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
          <>
            <div className={styles.lockBanner} data-testid="auto-paper-lock-notice">
              <strong>Simulation only.</strong> No real money orders can be placed
              from Auto Paper. Live trading remains locked and Auto-live remains
              locked in this build.
            </div>

            <section className={`${styles.card} ${postureClass}`}>
              <div className={styles.cardHeader}>
                <div className={styles.postureRow}>
                  <span className={`${styles.posturePill} ${posturePillClass}`}>
                    {card.posture}
                  </span>
                  <span className={styles.code}>
                    mode: {card.mode} / trading mode: {card.trading_control.trading_mode} /
                    arming: {card.trading_control.arming_state}
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
                <EnforcementChip label="Live trading" on={card.enforcement.live_trading_enabled} />
                <EnforcementChip
                  label="Live submission"
                  on={card.enforcement.live_order_submission_allowed}
                />
              </div>

              <div className={styles.metaGrid} data-testid="auto-paper-state-summary">
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Auto Paper selectable</span>
                  <span className={styles.metaValue}>{card.auto_paper_selectable ? "yes" : "no"}</span>
                </div>
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Auto Paper active</span>
                  <span className={styles.metaValue}>{card.auto_paper_active ? "active" : "inactive"}</span>
                </div>
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Auto Paper armed</span>
                  <span className={styles.metaValue}>{card.auto_paper_armed ? "armed" : "not armed"}</span>
                </div>
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Last check</span>
                  <span className={styles.metaValue}>{formatTimestamp(card.last_check_at)}</span>
                </div>
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Last action</span>
                  <span className={styles.metaValue}>{formatTimestamp(card.last_action_at)}</span>
                </div>
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Last decision</span>
                  <span className={styles.metaValue}>{card.last_decision}</span>
                </div>
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Open paper positions</span>
                  <span className={styles.metaValue}>
                    {card.open_paper_positions_count} / {card.max_open_paper_positions}
                  </span>
                </div>
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Live / Auto-live</span>
                  <span className={styles.metaValue}>
                    {card.live_trading_locked && card.auto_live_locked ? "locked" : "review"}
                  </span>
                </div>
              </div>

              <div className={styles.section}>
                <h3 className={styles.sectionTitle}>Operator next action</h3>
                <p className={styles.sectionBody} data-testid="auto-paper-next-action">
                  {card.operator_next_action}
                </p>
              </div>

              {card.last_block_reason && (
                <div className={styles.section}>
                  <h3 className={styles.sectionTitle}>Latest block reason</h3>
                  <p className={styles.sectionBody}>{card.last_block_reason}</p>
                </div>
              )}

              {card.trading_control.reasons.length > 0 && (
                <div className={styles.section}>
                  <h3 className={styles.sectionTitle}>Trading-control notes</h3>
                  <ul className={styles.list}>
                    {card.trading_control.reasons.map((reason, idx) => (
                      <li key={`reason-${idx}`} className={styles.listItem}>
                        {reason}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className={styles.section}>
                <h3 className={styles.sectionTitle}>Risk gate summary</h3>
                <div className={styles.gateGrid}>
                  {card.risk_gate_summary.map((item) => (
                    <GateItem key={item.label} item={item} />
                  ))}
                </div>
              </div>

              <div className={styles.section}>
                <h3 className={styles.sectionTitle}>Safety notes</h3>
                <ul className={styles.list}>
                  {card.safety_notes.map((note) => (
                    <li key={note} className={styles.listItem}>
                      {note}
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.section}>
                <h3 className={styles.sectionTitle}>Latest paper action</h3>
                {card.latest_paper_order ? (
                  <div className={styles.metaGrid}>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Order status</span>
                      <span className={styles.metaValue}>{card.latest_paper_order.status ?? "—"}</span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Side / direction</span>
                      <span className={styles.metaValue}>
                        {card.latest_paper_order.side ?? "—"} / {card.latest_paper_order.direction ?? "—"}
                      </span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Simulated size</span>
                      <span className={styles.metaValue}>{formatNumber(card.latest_paper_order.qty)}</span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Simulated notional</span>
                      <span className={styles.metaValue}>{formatNumber(card.latest_paper_order.notional)}</span>
                    </div>
                  </div>
                ) : (
                  <p className={styles.sectionBody}>No persisted Auto Paper action has been recorded yet.</p>
                )}
              </div>

              {card.latest_run && (
                <div className={styles.section}>
                  <h3 className={styles.sectionTitle}>Latest worker run</h3>
                  <div className={styles.metaGrid}>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Worker</span>
                      <span className={styles.metaValue}>{card.latest_run.worker_name}</span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Status</span>
                      <span className={styles.metaValue}>{card.latest_run.status}</span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Source</span>
                      <span className={styles.metaValue}>{card.latest_run.source}</span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Started</span>
                      <span className={styles.metaValue}>{formatTimestamp(card.latest_run.started_at)}</span>
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
          </>
        )}

        <div className={styles.driftLockNotice}>
          Drift lock active: this view is read-only. Nothing on this page can
          submit orders or change a gate.
        </div>
      </div>
    </main>
  );
}