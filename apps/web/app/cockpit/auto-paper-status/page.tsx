"use client";

// MH-COCKPIT-13-B / Auto Paper Cockpit + Operations Polish.
// Surfaces drift-lock posture and a small set of safe operator controls:
// run-one-paper-cycle, kill-switch activate/deactivate. No live controls,
// no MARKET order button, no auto-retry. All actions hit paper-only routes.

import { useCallback, useEffect, useState } from "react";

import {
  activateAutoPaperKillSwitch,
  deactivateAutoPaperKillSwitch,
  getAutoPaperKillSwitch,
  getAutoPaperStatusCard,
  runAutoPaperOnce,
  type AutoPaperKillSwitchState,
  type AutoPaperRunResult,
  type AutoPaperStatusCard,
  type AutoPaperStatusPosture,
  type AutoPaperStatusRiskGateItem,
} from "../../../lib/api/cockpitAutoPaperStatus";
import styles from "../../../styles/pages/auto-paper-status.module.css";

const STATUS_LOAD_TIMEOUT_MS = 8000;
const KILL_SWITCH_LOAD_TIMEOUT_MS = 3000;

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

function formatBool(value: boolean): string {
  return value ? "yes" : "no";
}

function formatMaybeNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return "\u2014";
  return `${value}`;
}

function withTimeout<T>(promise: Promise<T>, ms: number, label: string): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error(`${label} timed out after ${ms}ms`));
    }, ms);

    promise
      .then((value) => {
        clearTimeout(timer);
        resolve(value);
      })
      .catch((error: unknown) => {
        clearTimeout(timer);
        reject(error);
      });
  });
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

function deriveGuidance(card: AutoPaperStatusCard): string | null {
  const gate = card.controlled_gate;
  if (!gate) return null;
  const snap = gate.snapshot;
  if (snap.kill_switch_active) {
    return "Kill switch is active — no orders will be submitted. Deactivate below when you want to resume.";
  }
  if (snap.orders_today >= snap.max_orders_per_day) {
    return `Daily cap reached (${snap.orders_today}/${snap.max_orders_per_day}). No further paper orders today.`;
  }
  if (!gate.decision.allowed) {
    return `Gate blocked${gate.decision.blocking_gate ? ` at ${gate.decision.blocking_gate}` : ""}: ${gate.decision.reason ?? "no reason supplied"}.`;
  }
  const latest = card.latest_paper_order;
  if (latest && latest.ibkr_status && /presubmit|pending|api/i.test(latest.ibkr_status)) {
    return `Latest paper order ${latest.broker_order_id ?? ""} is ${latest.ibkr_status} at IBKR — resting on the book.`;
  }
  if (!card.live_trading_locked) {
    return "Live trading is not locked — running another paper cycle is disabled until it is.";
  }
  return "Gate is clear — one paper cycle can be submitted.";
}

export default function AutoPaperStatusPage() {
  const [card, setCard] = useState<AutoPaperStatusCard | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  const [runPending, setRunPending] = useState(false);
  const [runResult, setRunResult] = useState<AutoPaperRunResult | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  const [killSwitch, setKillSwitch] = useState<AutoPaperKillSwitchState | null>(null);
  const [killPending, setKillPending] = useState(false);
  const [killError, setKillError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await withTimeout(
        getAutoPaperStatusCard(),
        STATUS_LOAD_TIMEOUT_MS,
        "Auto Paper status request",
      );
      setCard(resp);
      setLastRefreshed(new Date());

      void withTimeout(
        getAutoPaperKillSwitch(),
        KILL_SWITCH_LOAD_TIMEOUT_MS,
        "Kill switch request",
      )
        .then((ks) => {
          setKillSwitch(ks);
        })
        .catch(() => {
          // Keep the primary status visible even if kill-switch state is temporarily unavailable.
        });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleRunOnce = useCallback(async () => {
    if (typeof window !== "undefined") {
      const ok = window.confirm(
        "Submit one auto-paper cycle to IBKR Paper Gateway? This will place at most one LIMIT order.",
      );
      if (!ok) return;
    }
    setRunPending(true);
    setRunError(null);
    setRunResult(null);
    try {
      const result = await runAutoPaperOnce();
      setRunResult(result);
      await load();
    } catch (err) {
      setRunError(err instanceof Error ? err.message : String(err));
    } finally {
      setRunPending(false);
    }
  }, [load]);

  const handleKillSwitchToggle = useCallback(
    async (activate: boolean) => {
      setKillPending(true);
      setKillError(null);
      try {
        const result = activate
          ? await activateAutoPaperKillSwitch()
          : await deactivateAutoPaperKillSwitch();
        setKillSwitch(result);
        await load();
      } catch (err) {
        setKillError(err instanceof Error ? err.message : String(err));
      } finally {
        setKillPending(false);
      }
    },
    [load],
  );

  const postureClass = card ? styles[card.posture] ?? "" : "";
  const posturePillClass = card ? POSTURE_CLASS[card.posture] : "";
  const gate = card?.controlled_gate;
  const snapshot = gate?.snapshot;
  const decision = gate?.decision;
  const symbolAllowlist = Array.isArray(snapshot?.symbol_allowlist)
    ? snapshot.symbol_allowlist
    : [];
  const ksActive = snapshot?.kill_switch_active ?? killSwitch?.kill_switch_active ?? false;

  const runDisabled =
    runPending ||
    !card ||
    !card.live_trading_locked ||
    !decision?.allowed ||
    snapshot?.broker_mode !== "paper" ||
    ksActive;

  const guidance = card ? deriveGuidance(card) : null;
  const candidateQueue = card?.candidate_queue;
  const queueHygiene = card?.queue_hygiene;
  const nextRunGuidance = card?.next_run_guidance;

  return (
    <main className={styles.page} data-testid="auto-paper-status-page">
      <div className={styles.container}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>Auto-Paper Status</h1>
            <p className={styles.subtitle}>
              Visibility and safe paper-only controls for the Auto Paper
              subsystem. Live trading and live submission remain locked; this
              page can only submit paper orders or toggle the kill switch.
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
              data-testid="auto-paper-refresh"
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

              {gate && snapshot && decision && (
                <div
                  className={styles.section}
                  data-testid="auto-paper-controlled-gate"
                >
                  <h3 className={styles.sectionTitle}>Controlled run gate</h3>
                  <div className={styles.gateBadgeRow}>
                    <span
                      className={`${styles.gateBadge} ${
                        decision.allowed ? styles.gateBadgeAllowed : styles.gateBadgeBlocked
                      }`}
                      data-testid="auto-paper-gate-decision"
                    >
                      GATE: {decision.allowed ? "ALLOWED" : "BLOCKED"}
                    </span>
                    {decision.blocking_gate && (
                      <span className={styles.code}>blocking gate: {decision.blocking_gate}</span>
                    )}
                  </div>
                  {decision.reason && (
                    <p className={styles.sectionBody}>{decision.reason}</p>
                  )}
                  <div className={styles.metaGrid}>
                    <div className={styles.metaItem} data-testid="auto-paper-daily-cap">
                      <span className={styles.metaLabel}>Daily cap</span>
                      <span className={styles.metaValue}>
                        {snapshot.orders_today} / {snapshot.max_orders_per_day}
                      </span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Per-run cap</span>
                      <span className={styles.metaValue}>{snapshot.max_orders_per_run}</span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Max notional (USD)</span>
                      <span className={styles.metaValue}>{formatNumber(snapshot.max_notional_usd)}</span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Order type</span>
                      <span className={styles.metaValue}>{snapshot.order_type}</span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Limit price</span>
                      <span className={styles.metaValue}>{formatNumber(snapshot.limit_price)}</span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Symbol allowlist</span>
                      <span className={styles.metaValue}>
                        {symbolAllowlist.length > 0
                          ? symbolAllowlist.join(", ")
                          : "—"}
                      </span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Broker provider</span>
                      <span className={styles.metaValue}>{snapshot.broker_provider}</span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Broker mode</span>
                      <span className={styles.metaValue}>{snapshot.broker_mode}</span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>TWS enabled</span>
                      <span className={styles.metaValue}>{formatBool(snapshot.tws_enabled)}</span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Auto paper enabled</span>
                      <span className={styles.metaValue}>{formatBool(snapshot.auto_paper_enabled)}</span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Background scheduler enabled</span>
                      <span className={styles.metaValue}>
                        {formatBool(snapshot.background_scheduler_enabled)}
                      </span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Minutes between runs</span>
                      <span className={styles.metaValue}>
                        {formatMaybeNumber(snapshot.minutes_between_runs)}
                      </span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Kill on error count</span>
                      <span className={styles.metaValue}>
                        {formatMaybeNumber(snapshot.kill_on_error_count)}
                      </span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Kill on reject rate</span>
                      <span className={styles.metaValue}>{formatNumber(snapshot.kill_on_reject_rate)}</span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Kill switch</span>
                      <span className={styles.metaValue}>
                        {snapshot.kill_switch_active ? "ACTIVE" : "inactive"}
                      </span>
                    </div>
                  </div>
                  {(snapshot.broker_mode !== "paper" || snapshot.live_execution_enabled) && (
                    <p className={styles.opsNote}>
                      Scheduler is effectively blocked until broker mode is paper and live execution remains disabled.
                    </p>
                  )}
                </div>
              )}

              {nextRunGuidance && (
                <div className={styles.section} data-testid="auto-paper-next-run-guidance">
                  <h3 className={styles.sectionTitle}>Next run guidance</h3>
                  <div className={styles.gateBadgeRow}>
                    <span
                      className={`${styles.gateBadge} ${
                        nextRunGuidance.can_run_now ? styles.gateBadgeAllowed : styles.gateBadgeBlocked
                      }`}
                    >
                      {nextRunGuidance.can_run_now ? "RUN NOW: YES" : "RUN NOW: NO"}
                    </span>
                    {nextRunGuidance.primary_blocking_gate && (
                      <span className={styles.code}>
                        primary gate: {nextRunGuidance.primary_blocking_gate}
                      </span>
                    )}
                  </div>
                  {nextRunGuidance.primary_reason && (
                    <p className={styles.sectionBody}>{nextRunGuidance.primary_reason}</p>
                  )}
                  <div className={styles.metaGrid}>
                    <div className={styles.metaItem} data-testid="auto-paper-next-run-daily-cap">
                      <span className={styles.metaLabel}>Daily cap state</span>
                      <span className={styles.metaValue}>
                        {nextRunGuidance.orders_today} / {nextRunGuidance.max_orders_per_day}
                      </span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Per-run cap</span>
                      <span className={styles.metaValue}>{nextRunGuidance.max_orders_per_run}</span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Background scheduler enabled</span>
                      <span className={styles.metaValue}>
                        {formatBool(nextRunGuidance.background_scheduler_enabled)}
                      </span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Live execution enabled</span>
                      <span className={styles.metaValue}>
                        {formatBool(nextRunGuidance.live_execution_enabled)}
                      </span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Safe for supervised session</span>
                      <span className={styles.metaValue}>
                        {formatBool(nextRunGuidance.safe_for_supervised_session)}
                      </span>
                    </div>
                  </div>
                  <p className={styles.opsNote}>{nextRunGuidance.suggested_operator_action}</p>
                </div>
              )}

              <div
                className={styles.section}
                data-testid="auto-paper-operations"
              >
                <h3 className={styles.sectionTitle}>Operations</h3>
                {guidance && (
                  <p className={styles.opsNote} data-testid="auto-paper-guidance">
                    {guidance}
                  </p>
                )}
                <div className={styles.opsActions}>
                  <button
                    type="button"
                    className={styles.primaryButton}
                    onClick={() => void handleRunOnce()}
                    disabled={runDisabled}
                    data-testid="auto-paper-run-button"
                  >
                    {runPending ? "Submitting…" : "Run one paper cycle"}
                  </button>
                  {ksActive ? (
                    <button
                      type="button"
                      className={styles.secondaryButton}
                      onClick={() => void handleKillSwitchToggle(false)}
                      disabled={killPending}
                      data-testid="auto-paper-kill-switch-deactivate"
                    >
                      {killPending ? "Working…" : "Deactivate kill switch"}
                    </button>
                  ) : (
                    <button
                      type="button"
                      className={styles.dangerButton}
                      onClick={() => void handleKillSwitchToggle(true)}
                      disabled={killPending}
                      data-testid="auto-paper-kill-switch-activate"
                    >
                      {killPending ? "Working…" : "Activate kill switch"}
                    </button>
                  )}
                </div>
                {runError && (
                  <p className={styles.opsResult} data-testid="auto-paper-run-error">
                    Run failed: {runError}
                  </p>
                )}
                {runResult && (
                  <p className={styles.opsResult} data-testid="auto-paper-run-result">
                    {runResult.worker_name}: {runResult.status} — {runResult.message}
                  </p>
                )}
                {killError && (
                  <p className={styles.opsResult} data-testid="auto-paper-kill-error">
                    Kill switch action failed: {killError}
                  </p>
                )}
                {killSwitch && (
                  <p className={styles.opsNote}>
                    Kill switch: {killSwitch.kill_switch_active ? "ACTIVE" : "inactive"}
                    {killSwitch.profile_name ? ` (profile: ${killSwitch.profile_name})` : ""}
                  </p>
                )}
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

              {candidateQueue && (
                <div className={styles.section} data-testid="auto-paper-candidate-queue">
                  <h3 className={styles.sectionTitle}>Top candidate queue</h3>
                  <p className={styles.sectionBody}>{candidateQueue.selection_explanation}</p>
                  <div className={styles.metaGrid}>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Eligible candidates</span>
                      <span className={styles.metaValue}>{candidateQueue.eligible_count}</span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Recency window</span>
                      <span className={styles.metaValue}>{candidateQueue.recency_hours}h</span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Min signal score</span>
                      <span className={styles.metaValue}>{formatNumber(candidateQueue.min_signal_score)}</span>
                    </div>
                  </div>
                  {candidateQueue.top_candidates.length > 0 ? (
                    <div className={styles.metaGrid}>
                      {candidateQueue.top_candidates.map((item) => (
                        <div className={styles.metaItem} key={item.signal_id}>
                          <span className={styles.metaLabel}>
                            {item.asset} ({item.provider_name})
                          </span>
                          <span className={styles.metaValue}>
                            score {formatNumber(item.signal_score)} / composite {formatNumber(item.composite_score)} / age {formatMaybeNumber(item.age_minutes)}m
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className={styles.sectionBody}>No eligible candidates in the current queue window.</p>
                  )}
                </div>
              )}

              {queueHygiene && (
                <div className={styles.section} data-testid="auto-paper-queue-hygiene">
                  <h3 className={styles.sectionTitle}>Queue hygiene</h3>
                  <div className={styles.metaGrid}>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Stale manual seeds</span>
                      <span className={styles.metaValue}>{queueHygiene.stale_manual_seed_count}</span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Duplicate-symbol candidates</span>
                      <span className={styles.metaValue}>{queueHygiene.duplicate_symbol_candidate_count}</span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Already submitted overlap</span>
                      <span className={styles.metaValue}>{queueHygiene.already_submitted_count}</span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Allowlist-blocked candidates</span>
                      <span className={styles.metaValue}>{queueHygiene.allowlist_blocked_count}</span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Cap blocked</span>
                      <span className={styles.metaValue}>{queueHygiene.cap_blocked ? "yes" : "no"}</span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Controlled gate blocked</span>
                      <span className={styles.metaValue}>{queueHygiene.controlled_gate_blocked ? "yes" : "no"}</span>
                    </div>
                  </div>
                  {queueHygiene.cleanup_recommendations.length > 0 && (
                    <ul className={styles.list}>
                      {queueHygiene.cleanup_recommendations.map((item) => (
                        <li key={item} className={styles.listItem}>
                          {item}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}

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
                      <span className={styles.metaLabel}>Order type</span>
                      <span className={styles.metaValue}>{card.latest_paper_order.order_type ?? "—"}</span>
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
                    <div className={styles.metaItem} data-testid="auto-paper-broker-order-id">
                      <span className={styles.metaLabel}>Broker order ID</span>
                      <span className={styles.metaValue}>
                        {card.latest_paper_order.broker_order_id ?? "—"}
                      </span>
                    </div>
                    <div className={styles.metaItem} data-testid="auto-paper-ibkr-status">
                      <span className={styles.metaLabel}>IBKR status</span>
                      <span className={styles.metaValue}>
                        {card.latest_paper_order.ibkr_status ?? "—"}
                      </span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Submitted</span>
                      <span className={styles.metaValue}>
                        {formatTimestamp(card.latest_paper_order.submitted_at)}
                      </span>
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
                <p className={styles.opsNote}>
                  <a
                    className={styles.timelineLink}
                    href="/cockpit/audit/broker-submit-decisions"
                    data-testid="auto-paper-timeline-link"
                  >
                    View broker submit timeline →
                  </a>
                </p>
              </div>
            </section>
          </>
        )}

        <div className={styles.driftLockNotice}>
          Drift lock active: live trading and live submission are locked.
          Controls on this page can only submit paper orders or toggle the
          kill switch.
        </div>
      </div>
    </main>
  );
}
