"use client";

import type {
  BrokerDailyPnl,
  BrokerHealth,
  BrokerTradingControl,
} from "../../lib/api/broker";
import styles from "../../styles/pages/broker.module.css";

type HealthState =
  | { status: "loading" }
  | { status: "ready"; data: BrokerHealth }
  | { status: "error" };

type ControlState =
  | { status: "loading" }
  | { status: "ready"; data: BrokerTradingControl }
  | { status: "error" };

function healthPanelClass(hs: HealthState): string {
  if (hs.status !== "ready") return `${styles.healthPanel} ${styles.healthPanelLoading}`;
  switch (hs.data.status) {
    case "paper_ready":
      return `${styles.healthPanel} ${styles.healthPanelReady}`;
    case "paper_config_only":
    case "live_config_only":
      return `${styles.healthPanel} ${styles.healthPanelConfigOnly}`;
    case "live_ready":
    case "misconfigured":
      return `${styles.healthPanel} ${styles.healthPanelMisconfigured}`;
  }
}

function BadgeDot({ hs }: { hs: HealthState }) {
  if (hs.status !== "ready") {
    return (
      <span className={`${styles.healthBadge} ${styles.healthBadgeLoading}`}>
        <span className={styles.healthBadgeDot} /> Checking…
      </span>
    );
  }
  switch (hs.data.status) {
    case "paper_ready":
      return (
        <span className={`${styles.healthBadge} ${styles.healthBadgeReady}`}>
          <span className={styles.healthBadgeDot} /> Paper Ready
        </span>
      );
    case "live_ready":
      return (
        <span className={`${styles.healthBadge} ${styles.healthBadgeMisconfigured}`}>
          <span className={styles.healthBadgeDot} /> Live Ready
        </span>
      );
    case "paper_config_only":
      return (
        <span className={`${styles.healthBadge} ${styles.healthBadgeConfigOnly}`}>
          <span className={styles.healthBadgeDot} /> Config Only
        </span>
      );
    case "live_config_only":
      return (
        <span className={`${styles.healthBadge} ${styles.healthBadgeConfigOnly}`}>
          <span className={styles.healthBadgeDot} /> Live Config Only
        </span>
      );
    case "misconfigured":
      return (
        <span className={`${styles.healthBadge} ${styles.healthBadgeMisconfigured}`}>
          <span className={styles.healthBadgeDot} /> Misconfigured
        </span>
      );
  }
}

function CheckPill({ pass, label, warn = false }: { pass: boolean; label: string; warn?: boolean }) {
  const cls = pass
    ? styles.healthCheckPass
    : warn
      ? styles.healthCheckWarn
      : styles.healthCheckFail;
  return (
    <span className={`${styles.healthCheck} ${cls}`}>
      <span className={styles.healthCheckIcon}>{pass ? "✓" : warn ? "~" : "✗"}</span>
      {label}
    </span>
  );
}

export function BrokerHealthPanel({ hs }: { hs: HealthState }) {
  const healthStatus = hs.status === "ready" ? hs.data.status : hs.status;
  return (
    <div
      className={healthPanelClass(hs)}
      data-testid="broker-health-panel"
      data-health-status={healthStatus}
    >
      <BadgeDot hs={hs} />
      {hs.status === "ready" && (
        <>
          <div className={styles.healthChecks}>
            <span data-testid="broker-health-mode-guard">
              <CheckPill pass={hs.data.mode_guard_ok} label="Mode Guard" />
            </span>
            <span data-testid="broker-health-gateway">
              <CheckPill
                pass={hs.data.gateway_reachable}
                label="Gateway"
                warn={!hs.data.gateway_reachable && hs.data.mode_guard_ok}
              />
            </span>
            <span data-testid="broker-health-account">
              <CheckPill
                pass={hs.data.account_is_paper}
                label={hs.data.account_id ? `Account ${hs.data.account_id}` : "Account"}
              />
            </span>
          </div>
          <span
            className={styles.healthGatewayUrl}
            title={hs.data.gateway_url}
            data-testid="broker-health-gateway-url"
          >
            {hs.data.gateway_url}
          </span>
        </>
      )}
      {hs.status === "loading" && (
        <span className={`${styles.healthCheck} ${styles.healthCheckNeutral}`}>Loading health check…</span>
      )}
      {hs.status === "error" && (
        <span className={`${styles.healthCheck} ${styles.healthCheckWarn}`}>Health check unavailable</span>
      )}
    </div>
  );
}

function controlPanelClass(cs: ControlState): string {
  if (cs.status !== "ready") return `${styles.controlPanel} ${styles.controlPanelLoading}`;
  if (cs.data.emergency_stop_active || cs.data.arming_state === "emergency_stopped") {
    return `${styles.controlPanel} ${styles.controlPanelStopped}`;
  }
  if (cs.data.trading_mode === "live") {
    return `${styles.controlPanel} ${styles.controlPanelLive}`;
  }
  return `${styles.controlPanel} ${styles.controlPanelPaper}`;
}

function controlBadgeClass(cs: ControlState): string {
  if (cs.status !== "ready") return `${styles.controlBadge} ${styles.controlBadgeLoading}`;
  if (cs.data.emergency_stop_active || cs.data.arming_state === "emergency_stopped") {
    return `${styles.controlBadge} ${styles.controlBadgeStopped}`;
  }
  if (cs.data.trading_mode === "live") {
    return `${styles.controlBadge} ${styles.controlBadgeLive}`;
  }
  return `${styles.controlBadge} ${styles.controlBadgePaper}`;
}

function ControlStatusPill({
  label,
  allowed,
  neutral = false,
}: {
  label: string;
  allowed: boolean;
  neutral?: boolean;
}) {
  const cls = neutral
    ? styles.controlValueNeutral
    : allowed
      ? styles.controlValueAllowed
      : styles.controlValueBlocked;
  return <span className={`${styles.controlValueBadge} ${cls}`}>{label}</span>;
}

export function BrokerTradingControlPanel({
  cs,
  formatControlValue,
}: {
  cs: ControlState;
  formatControlValue: (value: string) => string;
}) {
  const controlStatus = cs.status === "ready" ? cs.data.trading_mode : cs.status;

  return (
    <section
      className={controlPanelClass(cs)}
      data-testid="broker-control-panel"
      data-control-status={controlStatus}
    >
      <div className={styles.controlHeaderRow}>
        <div>
          <h2 className={styles.sectionTitle}>Trading Control</h2>
          {cs.status === "ready" && cs.data.trading_mode === "paper" && (
            <p className={styles.controlSummary} data-testid="broker-control-summary-paper">
              Paper mode active, IBKR paper orders only.
            </p>
          )}
          {cs.status === "ready" && cs.data.trading_mode === "live" && (
            <p className={styles.controlSummary} data-testid="broker-control-summary-live">
              Live mode configured, live execution remains locked until future arming gates are enabled.
            </p>
          )}
          {cs.status === "loading" && (
            <p className={styles.controlSummary}>Loading trading control...</p>
          )}
          {cs.status === "error" && (
            <p className={styles.controlSummary}>Trading control unavailable</p>
          )}
        </div>
        <span className={controlBadgeClass(cs)} data-testid="broker-control-badge">
          {cs.status === "ready"
            ? cs.data.trading_mode === "paper"
              ? "Paper Mode"
              : "Live Configured"
            : cs.status === "loading"
              ? "Checking"
              : "Unavailable"}
        </span>
      </div>

      {cs.status === "ready" && (
        <>
          <div className={styles.controlGrid}>
            <div className={styles.controlItem} data-testid="broker-control-trading-mode">
              <span className={styles.controlLabel}>Trading mode</span>
              <span className={styles.controlValueText}>{formatControlValue(cs.data.trading_mode)}</span>
            </div>
            <div className={styles.controlItem} data-testid="broker-control-execution-control">
              <span className={styles.controlLabel}>Execution control</span>
              <span className={styles.controlValueText}>{formatControlValue(cs.data.execution_control)}</span>
            </div>
            <div className={styles.controlItem} data-testid="broker-control-arming-state">
              <span className={styles.controlLabel}>Arming state</span>
              <span className={styles.controlValueText}>{formatControlValue(cs.data.arming_state)}</span>
            </div>
            <div className={styles.controlItem} data-testid="broker-control-paper-submit">
              <span className={styles.controlLabel}>Paper order submission</span>
              <ControlStatusPill
                label={cs.data.paper_order_submission_allowed ? "Allowed" : "Blocked"}
                allowed={cs.data.paper_order_submission_allowed}
              />
            </div>
            <div className={styles.controlItem} data-testid="broker-control-live-submit">
              <span className={styles.controlLabel}>Live order submission</span>
              <ControlStatusPill
                label={cs.data.live_order_submission_allowed ? "Allowed" : "Blocked"}
                allowed={cs.data.live_order_submission_allowed}
              />
            </div>
            <div className={styles.controlItem} data-testid="broker-control-auto-trading">
              <span className={styles.controlLabel}>Auto trading</span>
              <ControlStatusPill
                label={cs.data.auto_trading_allowed ? "Allowed" : "Blocked"}
                allowed={cs.data.auto_trading_allowed}
              />
            </div>
            <div className={styles.controlItem} data-testid="broker-control-emergency-stop">
              <span className={styles.controlLabel}>Emergency stop</span>
              <ControlStatusPill
                label={cs.data.emergency_stop_active ? "Active" : "Clear"}
                allowed={!cs.data.emergency_stop_active}
                neutral={!cs.data.emergency_stop_active}
              />
            </div>
          </div>

          <div className={styles.controlNotes}>
            {!cs.data.live_order_submission_allowed && (
              <p className={styles.controlNote} data-testid="broker-control-live-blocked-note">
                Live order submission blocked.
              </p>
            )}
            {!cs.data.auto_trading_allowed && (
              <p className={styles.controlNote} data-testid="broker-control-auto-locked-note">
                Auto trading locked.
              </p>
            )}
          </div>

          <div className={styles.controlReasons} data-testid="broker-control-reasons">
            <span className={styles.controlReasonsTitle}>Blocked reasons / safety notes</span>
            {cs.data.reasons.length > 0 ? (
              <ul className={styles.controlReasonsList}>
                {cs.data.reasons.map((reason, index) => (
                  <li key={`${reason}-${index}`} className={styles.controlReasonItem}>
                    {formatControlValue(reason)}
                  </li>
                ))}
              </ul>
            ) : (
              <p className={styles.controlReasonFallback}>No additional blocked reasons reported.</p>
            )}
          </div>
        </>
      )}

      {cs.status === "error" && (
        <span className={`${styles.healthCheck} ${styles.healthCheckWarn}`} data-testid="broker-control-unavailable">
          Trading control unavailable
        </span>
      )}
    </section>
  );
}

export function BrokerDailyPnlStrip({
  dailyPnl,
  formatMoney,
}: {
  dailyPnl: BrokerDailyPnl;
  formatMoney: (value: number, currency?: string) => string;
}) {
  return (
    <div className={styles.dailyPnlStrip} data-testid="broker-daily-pnl-strip">
      <span className={styles.dailyPnlLabel}>Today&apos;s P&amp;L</span>
      <span
        className={dailyPnl.daily_pnl !== null && dailyPnl.daily_pnl < 0 ? styles.dailyPnlNegative : styles.dailyPnlPositive}
        data-testid="broker-daily-pnl-value"
      >
        {dailyPnl.daily_pnl !== null ? formatMoney(dailyPnl.daily_pnl) : "—"}
      </span>
      {dailyPnl.daily_loss !== null && dailyPnl.daily_loss > 0 && (
        <span className={styles.dailyPnlLoss} data-testid="broker-daily-loss-value">
          Loss: {formatMoney(dailyPnl.daily_loss)}
        </span>
      )}
      <span className={styles.dailyPnlNote}>
        {dailyPnl.snapshot_count} snapshot{dailyPnl.snapshot_count !== 1 ? "s" : ""} · active account
      </span>
    </div>
  );
}