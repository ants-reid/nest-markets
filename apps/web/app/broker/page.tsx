"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { BrokerAuditPanel } from "./audit-panel";
import {
  BrokerManualSubmitPanel,
  type SubmitFormErrors,
  type SubmitFormState,
} from "./manual-submit-panel";
import {
  BrokerDailyPnlStrip,
  BrokerHealthPanel,
  BrokerTradingControlPanel,
} from "./overview-panels";
import { BrokerTradeProvenancePanel } from "./provenance-panel";
import { BrokerReadinessChecklistPanel } from "./review-parent-panel";
import {
  formatTimestamp,
  type CopyState,
} from "./review-helpers";
import {
  getBrokerAccount,
  getBrokerControl,
  getBrokerPositions,
  getBrokerHealth,
  getBrokerOrderAudit,
  getDailyPnl,
  getNormalizedBrokerTrades,
  dryRunBrokerOrder,
  submitBrokerOrder,
  type BrokerAccountInfo,
  type BrokerDailyPnl,
  type BrokerTradingControl,
  type BrokerPosition,
  type BrokerHealth,
  type BrokerOrderAuditEntry,
  type BrokerOrderRequest,
  type BrokerOrderDryRunRequest,
  type BrokerOrderDryRunResult,
  type BrokerTradeEventAuditTrail,
} from "../../lib/api/broker";
import { useLivePolling } from "../../lib/hooks/useLivePolling";
import styles from "../../styles/pages/broker.module.css";

function formatMoney(value: number, currency = "USD"): string {
  return value.toLocaleString("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function pnlClass(value: number | null, css: typeof styles): string {
  if (value === null) return styles.td;
  return value >= 0 ? styles.pnlPositive : styles.pnlNegative;
}

type PageState =
  | { status: "loading" }
  | { status: "ready"; account: BrokerAccountInfo; positions: BrokerPosition[] }
  | { status: "error"; message: string };

type HealthState =
  | { status: "loading" }
  | { status: "ready"; data: BrokerHealth }
  | { status: "error" };

type AuditState =
  | { status: "loading" }
  | { status: "ready"; entries: BrokerOrderAuditEntry[] }
  | { status: "error" };

type ProvenanceState =
  | { status: "loading" }
  | { status: "ready"; data: BrokerTradeEventAuditTrail }
  | { status: "error" };

type ControlState =
  | { status: "loading" }
  | { status: "ready"; data: BrokerTradingControl }
  | { status: "error" };

function sideBadgeClass(side: string | null): string {
  if (side === "BUY") return `${styles.sideBadge} ${styles.sideLong}`;
  if (side === "SELL") return `${styles.sideBadge} ${styles.sideShort}`;
  return styles.sideBadge;
}

function labelizeControlValue(value: string): string {
  return value
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function downloadTextFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(objectUrl);
}

async function copyTextToClipboard(text: string, setState: (next: CopyState) => void) {
  try {
    await navigator.clipboard.writeText(text);
    setState("copied");
  } catch {
    setState("error");
  }
}

// ── Page ─────────────────────────────────────────────────────────────────────


export default function BrokerPage() {
  const sectionNavItems = [
    { href: "#broker-overview", label: "Overview" },
    { href: "#broker-execution", label: "Manual Review" },
    { href: "#broker-positions", label: "Positions" },
    { href: "#broker-provenance", label: "Provenance" },
    { href: "#broker-audit", label: "Audit" },
  ] as const;

  const [state, setState] = useState<PageState>({ status: "loading" });
  const [health, setHealth] = useState<HealthState>({ status: "loading" });
  const [audit, setAudit] = useState<AuditState>({ status: "loading" });
  const [provenance, setProvenance] = useState<ProvenanceState>({ status: "loading" });
  const [control, setControl] = useState<ControlState>({ status: "loading" });
  const [dailyPnl, setDailyPnl] = useState<BrokerDailyPnl | null>(null);
  const [form, setForm] = useState<SubmitFormState>({
    ticker: "AAPL",
    side: "BUY",
    quantity: "10",
    orderType: "MARKET",
    limitPrice: "",
  });
  const [dryRun, setDryRun] = useState<BrokerOrderDryRunResult | null>(null);
  const [dryRunError, setDryRunError] = useState<string | null>(null);
  const [submitMessage, setSubmitMessage] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [runningDryRun, setRunningDryRun] = useState(false);
  const [runningSubmit, setRunningSubmit] = useState(false);
  const [formErrors, setFormErrors] = useState<SubmitFormErrors>({});
  const [confirmPending, setConfirmPending] = useState(false);

  async function load() {
    setState({ status: "loading" });
    try {
      const [account, positions] = await Promise.all([
        getBrokerAccount(),
        getBrokerPositions(),
      ]);
      setState({ status: "ready", account, positions });
    } catch (e) {
      setState({ status: "error", message: e instanceof Error ? e.message : "Failed to load broker data." });
    }
  }

  async function loadHealth() {
    try {
      const data = await getBrokerHealth();
      setHealth({ status: "ready", data });
    } catch {
      setHealth({ status: "error" });
    }
  }

  async function loadAudit() {
    try {
      const data = await getBrokerOrderAudit(20);
      setAudit({ status: "ready", entries: data.entries });
    } catch {
      setAudit({ status: "error" });
    }
  }

  async function loadControl() {
    try {
      const data = await getBrokerControl();
      setControl({ status: "ready", data });
    } catch {
      setControl({ status: "error" });
    }
  }

  async function loadProvenance() {
    try {
      const data = await getNormalizedBrokerTrades(50);
      setProvenance({ status: "ready", data });
    } catch {
      setProvenance({ status: "error" });
    }
  }

  async function loadDailyPnl() {
    try {
      const data = await getDailyPnl();
      setDailyPnl(data);
    } catch {
      // Non-fatal: daily P&L is advisory context only. Silently ignore failures.
      setDailyPnl(null);
    }
  }

  function buildOrderPayload(): BrokerOrderRequest {
    const quantity = Number(form.quantity);
    return {
      ticker: form.ticker.trim().toUpperCase(),
      side: form.side,
      quantity,
      order_type: form.orderType,
      limit_price: form.orderType === "LIMIT" && form.limitPrice ? Number(form.limitPrice) : undefined,
    };
  }

  function buildDryRunPayload(): BrokerOrderDryRunRequest {
    const base = buildOrderPayload();
    const payload: BrokerOrderDryRunRequest = { ...base };

    if (state.status === "ready") {
      payload.cash_balance = state.account.cash_balance;
      payload.buying_power = state.account.buying_power;
      payload.open_position_count = state.positions.length;

      // current_total_exposure: sum of market_value of all positions
      const totalExposure = state.positions.reduce(
        (sum, p) => sum + (p.market_value ?? p.quantity * (p.market_price ?? p.avg_cost)),
        0,
      );
      payload.current_total_exposure = totalExposure;

      // current_symbol_exposure: market value of positions matching form ticker
      const ticker = form.ticker.trim().toUpperCase();
      const symbolExposure = state.positions
        .filter((p) => p.ticker === ticker)
        .reduce(
          (sum, p) => sum + (p.market_value ?? p.quantity * (p.market_price ?? p.avg_cost)),
          0,
        );
      if (symbolExposure > 0) {
        payload.current_symbol_exposure = symbolExposure;
      }
    }

    // daily_pnl / daily_loss from GET /broker/daily-pnl (MH-44)
    // Only send when real data is available (snapshot_count > 0)
    if (dailyPnl !== null && dailyPnl.snapshot_count > 0) {
      if (dailyPnl.daily_pnl !== null) payload.daily_pnl = dailyPnl.daily_pnl;
      if (dailyPnl.daily_loss !== null) payload.daily_loss = dailyPnl.daily_loss;
    }

    return payload;
  }

  function validateForm(): SubmitFormErrors {
    const errors: SubmitFormErrors = {};
    if (!form.ticker.trim()) {
      errors.ticker = "Symbol is required";
    } else if (!/^[A-Za-z0-9.]{1,10}$/.test(form.ticker.trim())) {
      errors.ticker = "Use letters, numbers, or dot (max 10)";
    }
    const qty = Number(form.quantity);
    if (!form.quantity || Number.isNaN(qty) || qty <= 0 || !Number.isInteger(qty)) {
      errors.quantity = "Quantity must be a positive whole number";
    }
    if (form.orderType === "LIMIT") {
      const lp = Number(form.limitPrice);
      if (!form.limitPrice || Number.isNaN(lp) || lp <= 0) {
        errors.limitPrice = "Limit price must be > 0";
      }
    }
    return errors;
  }

  async function runDryRun() {
    const errors = validateForm();
    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      return;
    }
    setFormErrors({});
    setRunningDryRun(true);
    setDryRun(null);
    setDryRunError(null);
    setSubmitError(null);
    setSubmitMessage(null);
    try {
      const result = await dryRunBrokerOrder(buildDryRunPayload());
      setDryRun(result);
      await loadAudit();
    } catch (e) {
      setDryRunError(e instanceof Error ? e.message : "Dry run failed");
    } finally {
      setRunningDryRun(false);
    }
  }

  function handleSubmitClick() {
    if (!dryRun || dryRun.status !== "ready") {
      setSubmitError("Run a successful dry run before submitting.");
      return;
    }
    setConfirmPending(true);
    setSubmitError(null);
  }

  async function runSubmit() {
    if (!dryRun || dryRun.status !== "ready") {
      setSubmitError("Run a successful dry run before submitting.");
      setConfirmPending(false);
      return;
    }
    setConfirmPending(false);
    setRunningSubmit(true);
    setSubmitError(null);
    setSubmitMessage(null);
    try {
      const result = await submitBrokerOrder(buildOrderPayload());
      setSubmitMessage(`Order submitted: ${result.broker_order_id} (${result.status})`);
      setDryRun(null);
      setForm({ ticker: "", side: "BUY", quantity: "", orderType: "MARKET", limitPrice: "" });
      await Promise.all([load(), loadAudit(), loadProvenance()]);
    } catch (e) {
      setSubmitError(e instanceof Error ? e.message : "Order submission failed");
      await loadAudit();
    } finally {
      setRunningSubmit(false);
    }
  }

  useEffect(() => {
    void load();
    void loadHealth();
    void loadAudit();
    void loadControl();
    void loadProvenance();
    void loadDailyPnl();
  }, []);
  useLivePolling(() => load(), 15000, { enabled: true, runImmediately: false });
  useLivePolling(() => loadHealth(), 30000, { enabled: true, runImmediately: false });
  useLivePolling(() => loadAudit(), 30000, { enabled: true, runImmediately: false });
  useLivePolling(() => loadControl(), 30000, { enabled: true, runImmediately: false });
  useLivePolling(() => loadProvenance(), 30000, { enabled: true, runImmediately: false });
  useLivePolling(() => loadDailyPnl(), 60000, { enabled: true, runImmediately: false });

  const readinessPanelProps = {
    state,
    health,
    control,
    dailyPnl,
    dryRun,
    provenance,
    audit,
    formatControlValue: labelizeControlValue,
    downloadTextFile,
    copyTextToClipboard,
  };

  const manualSubmitPanelProps = {
    form,
    setForm,
    formErrors,
    setFormErrors,
    dryRun,
    setDryRun,
    dryRunError,
    submitMessage,
    submitError,
    runningDryRun,
    runningSubmit,
    confirmPending,
    setConfirmPending,
    runDryRun,
    handleSubmitClick,
    runSubmit,
    formatMoney,
  };

  const provenancePanelProps = {
    provenance,
    formatTimestamp,
    formatMoney,
    getPnlClassName: (value: number | null) => pnlClass(value, styles),
    getSideBadgeClass: sideBadgeClass,
    downloadTextFile,
    copyTextToClipboard,
  };

  const accountMetrics =
    state.status === "ready"
      ? [
          { label: "Net Liquidation", value: formatMoney(state.account.net_liquidation, state.account.currency) },
          { label: "Cash Balance", value: formatMoney(state.account.cash_balance, state.account.currency) },
          { label: "Buying Power", value: formatMoney(state.account.buying_power, state.account.currency) },
          { label: "Excess Liquidity", value: formatMoney(state.account.excess_liquidity, state.account.currency) },
          {
            label: "Margin Used",
            value: formatMoney(state.account.margin, state.account.currency),
            valueClassName: state.account.margin > 0 ? styles.metricValueNegative : "",
          },
          {
            label: "Unrealized P&L",
            value: formatMoney(state.account.unrealized_pnl, state.account.currency),
            valueClassName:
              state.account.unrealized_pnl >= 0 ? styles.metricValuePositive : styles.metricValueNegative,
          },
        ]
      : [];

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <div className={styles.pageHeader}>
          <h1 className={styles.pageTitle}>Portfolio</h1>
          <div className={styles.headerActions}>
            {state.status === "ready" && (
              <span className={styles.accountId}>{state.account.currency} · DUP153837</span>
            )}
            <button type="button" onClick={() => void load()} className={styles.refreshButton}>
              Refresh
            </button>
          </div>
        </div>
        <p className={styles.subtitle}>
          Live account summary and open positions from IBKR paper account.
        </p>

        <nav className={styles.sectionNav} aria-label="Broker review sections" data-testid="broker-section-nav">
          {sectionNavItems.map((item) => (
            <a key={item.href} href={item.href} className={styles.sectionNavLink}>
              {item.label}
            </a>
          ))}
        </nav>

        {state.status === "loading" && <p className={styles.loadingMsg}>Loading…</p>}
        {state.status === "error" && <p className={styles.errorMsg}>{state.message}</p>}

        <section id="broker-overview" className={styles.pageSection} data-testid="broker-overview-section">
          <div className={styles.sectionHeadingRow}>
            <div>
              <p className={styles.sectionEyebrow}>Overview</p>
              <h2 className={styles.sectionGroupTitle}>Broker readiness and account posture</h2>
            </div>
            <p className={styles.sectionGroupHint}>Health, control status, and current-day context remain visible at the top of the review flow.</p>
          </div>

          <div className={styles.overviewStack}>
            <BrokerReadinessChecklistPanel {...readinessPanelProps} />
            <BrokerHealthPanel hs={health} />
            <BrokerTradingControlPanel cs={control} formatControlValue={labelizeControlValue} />

            {dailyPnl !== null && dailyPnl.snapshot_count > 0 && (
              <BrokerDailyPnlStrip dailyPnl={dailyPnl} formatMoney={formatMoney} />
            )}
          </div>
        </section>

        <section id="broker-execution" className={styles.pageSection} data-testid="broker-execution-section">
          <div className={styles.sectionHeadingRow}>
            <div>
              <p className={styles.sectionEyebrow}>Execution Review</p>
              <h2 className={styles.sectionGroupTitle}>Manual paper order workflow</h2>
            </div>
            <p className={styles.sectionGroupHint}>Dry-run, advisory context, and confirmation safeguards are unchanged.</p>
          </div>

          <BrokerManualSubmitPanel {...manualSubmitPanelProps} />
        </section>

        {state.status === "ready" && (
          <section id="broker-positions" className={styles.pageSection} data-testid="broker-review-section">
            <div className={styles.sectionHeadingRow}>
              <div>
                <p className={styles.sectionEyebrow}>Review Surfaces</p>
                <h2 className={styles.sectionGroupTitle}>Positions, provenance, and audit trail</h2>
              </div>
              <p className={styles.sectionGroupHint}>Open positions stay prominent, while provenance and audit history are grouped for faster inspection.</p>
            </div>

            {/* Account metrics */}
            <div className={styles.metricsRow}>
              {accountMetrics.map((metric) => (
                <div key={metric.label} className={styles.metricCard}>
                  <div className={styles.metricLabel}>{metric.label}</div>
                  <div className={`${styles.metricValue} ${metric.valueClassName ?? ""}`.trim()}>{metric.value}</div>
                </div>
              ))}
            </div>

            {/* Positions */}
            <h2 className={styles.sectionTitle}>Open Positions ({state.positions.length})</h2>

            {state.positions.length === 0 ? (
              <div className={styles.emptyPositions}>
                No open positions. Paper account is flat.
              </div>
            ) : (
              <div className={styles.tableWrapper}>
                <table className={styles.table}>
                  <thead className={styles.thead}>
                    <tr>
                      {["Ticker", "Class", "Side", "Quantity", "Avg Cost", "Market Price", "Market Value", "Unrealized P&L"].map((h) => (
                        <th key={h} className={styles.th}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {state.positions.map((pos) => {
                      const sideClass = pos.side === "BUY" ? styles.sideLong : styles.sideShort;
                      return (
                        <tr key={pos.conid} className={styles.tr}>
                          <td className={styles.tdTicker}>
                            <Link href={`/signals?asset=${encodeURIComponent(pos.ticker)}`} style={{ color: "inherit", textDecoration: "none" }}>
                              {pos.ticker}
                            </Link>
                          </td>
                          <td className={styles.tdMuted}>{pos.asset_class}</td>
                          <td className={styles.td}>
                            <span className={`${styles.sideBadge} ${sideClass}`}>{pos.side}</span>
                          </td>
                          <td className={styles.td}>{pos.quantity.toLocaleString()}</td>
                          <td className={styles.td}>{formatMoney(pos.avg_cost, pos.currency)}</td>
                          <td className={styles.td}>
                            {pos.market_price !== null ? formatMoney(pos.market_price, pos.currency) : "—"}
                          </td>
                          <td className={styles.td}>
                            {pos.market_value !== null ? formatMoney(pos.market_value, pos.currency) : "—"}
                          </td>
                          <td className={pnlClass(pos.unrealized_pnl, styles)}>
                            {pos.unrealized_pnl !== null
                              ? `${pos.unrealized_pnl >= 0 ? "+" : ""}${formatMoney(pos.unrealized_pnl, pos.currency)}`
                              : "—"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        )}

        <div className={styles.reviewGrid}>
          <div id="broker-provenance" className={styles.reviewGridPrimary}>
            <BrokerTradeProvenancePanel {...provenancePanelProps} />
          </div>
          <div id="broker-audit" className={styles.reviewGridSecondary}>
            <BrokerAuditPanel audit={audit} formatTimestamp={formatTimestamp} />
          </div>
        </div>
      </div>
    </main>
  );
}
