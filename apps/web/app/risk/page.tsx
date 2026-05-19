"use client";

import Link from "next/link";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import { FormSection } from "../../components/FormSection";
import { LearnTooltip } from "../../components/LearnTooltip";
import styles from "../../styles/pages/risk.module.css";
import { evaluateRisk, getOpportunities, type RankedOpportunity } from "../../lib/api";
import { useLivePolling } from "../../lib/hooks/useLivePolling";
import type { ExecutionMode, RiskDecisionResponse, SignalDirection, SignalResponse, Timeframe } from "../../lib/types";

interface RiskFormState {
  asset: string;
  timeframe: Timeframe;
  direction: SignalDirection;
  shouldTrade: boolean;
  confidence: string;
  signalScore: string;
  spreadBps: string;
  dailyDrawdownPct: string;
  consecutiveLosses: string;
  minutesSinceLastLoss: string;
  correlatedExposureCount: string;
  openPositionsCount: string;
  marketQualityFlag: boolean;
  sessionAllowed: boolean;
  killSwitchActive: boolean;
  accountEquity: string;
  requestedExecutionMode: ExecutionMode;
}

const initialState: RiskFormState = {
  asset: "EURUSD",
  timeframe: "1h",
  direction: "long",
  shouldTrade: true,
  confidence: "0.65",
  signalScore: "72",
  spreadBps: "10",
  dailyDrawdownPct: "1",
  consecutiveLosses: "0",
  minutesSinceLastLoss: "",
  correlatedExposureCount: "0",
  openPositionsCount: "0",
  marketQualityFlag: true,
  sessionAllowed: true,
  killSwitchActive: false,
  accountEquity: "50000",
  requestedExecutionMode: "paper",
};

interface AssetBaseline {
  name: string;
  asset_class: string;
  composite_baseline_prior: number;
  historical_asset_win_rate: number;
  confidence_floor: number;
  signal_score_floor: number;
  risk_per_trade_bp: number;
  spread_bps_cap: number;
  daily_drawdown_stop_pct: number;
  cooldown_after_losses_min: number;
  loss_streak_trigger: number;
  max_correlated_exposure_count: number;
  max_open_positions_in_group: number;
  default_execution_mode: string;
  position_cap_multiple: number;
  primary_setup: string;
  primary_regime: string;
  notes: string;
}

const ASSET_BASELINES: Record<string, AssetBaseline> = {
  AAPL: { name: "Apple Inc.", asset_class: "equity", composite_baseline_prior: 0.6516, historical_asset_win_rate: 0.65, confidence_floor: 0.64, signal_score_floor: 70, risk_per_trade_bp: 60, spread_bps_cap: 20, daily_drawdown_stop_pct: 1.75, cooldown_after_losses_min: 30, loss_streak_trigger: 3, max_correlated_exposure_count: 2, max_open_positions_in_group: 4, default_execution_mode: "paper", position_cap_multiple: 1.0, primary_setup: "breakout_confirmation", primary_regime: "breakout", notes: "" },
  EURUSD: { name: "EUR/USD", asset_class: "fx", composite_baseline_prior: 0.4898, historical_asset_win_rate: 0.4286, confidence_floor: 0.65, signal_score_floor: 71, risk_per_trade_bp: 45, spread_bps_cap: 10, daily_drawdown_stop_pct: 1.25, cooldown_after_losses_min: 45, loss_streak_trigger: 3, max_correlated_exposure_count: 2, max_open_positions_in_group: 2, default_execution_mode: "paper", position_cap_multiple: 0.8, primary_setup: "trend_pullback", primary_regime: "range", notes: "FX major, rate-sensitive; require cleaner spread and stronger confirmation." },
  GBPUSD: { name: "GBP/USD", asset_class: "fx", composite_baseline_prior: 0.5338, historical_asset_win_rate: 0.5217, confidence_floor: 0.64, signal_score_floor: 70, risk_per_trade_bp: 45, spread_bps_cap: 10, daily_drawdown_stop_pct: 1.25, cooldown_after_losses_min: 45, loss_streak_trigger: 3, max_correlated_exposure_count: 2, max_open_positions_in_group: 2, default_execution_mode: "paper", position_cap_multiple: 0.85, primary_setup: "trend_pullback", primary_regime: "trend", notes: "" },
  GLD: { name: "SPDR Gold Shares", asset_class: "commodity_proxy", composite_baseline_prior: 0.5066, historical_asset_win_rate: 0.4545, confidence_floor: 0.66, signal_score_floor: 71, risk_per_trade_bp: 45, spread_bps_cap: 15, daily_drawdown_stop_pct: 1.25, cooldown_after_losses_min: 45, loss_streak_trigger: 3, max_correlated_exposure_count: 1, max_open_positions_in_group: 1, default_execution_mode: "paper", position_cap_multiple: 0.85, primary_setup: "breakout_confirmation", primary_regime: "risk_off", notes: "Favor macro, commodity, and geopolitical catalysts." },
  MSFT: { name: "Microsoft Corporation", asset_class: "equity", composite_baseline_prior: 0.5957, historical_asset_win_rate: 0.6538, confidence_floor: 0.63, signal_score_floor: 69, risk_per_trade_bp: 60, spread_bps_cap: 20, daily_drawdown_stop_pct: 1.75, cooldown_after_losses_min: 30, loss_streak_trigger: 3, max_correlated_exposure_count: 2, max_open_positions_in_group: 4, default_execution_mode: "paper", position_cap_multiple: 1.0, primary_setup: "trend_pullback", primary_regime: "trend", notes: "" },
  NVDA: { name: "NVIDIA Corporation", asset_class: "equity", composite_baseline_prior: 0.5859, historical_asset_win_rate: 0.5185, confidence_floor: 0.63, signal_score_floor: 70, risk_per_trade_bp: 50, spread_bps_cap: 20, daily_drawdown_stop_pct: 1.75, cooldown_after_losses_min: 30, loss_streak_trigger: 3, max_correlated_exposure_count: 2, max_open_positions_in_group: 4, default_execution_mode: "paper", position_cap_multiple: 0.9, primary_setup: "breakout_confirmation", primary_regime: "breakout", notes: "High-beta single-name; keep thresholds tighter." },
  QQQ: { name: "Invesco QQQ Trust", asset_class: "etf", composite_baseline_prior: 0.5807, historical_asset_win_rate: 0.5, confidence_floor: 0.61, signal_score_floor: 67, risk_per_trade_bp: 70, spread_bps_cap: 12, daily_drawdown_stop_pct: 1.5, cooldown_after_losses_min: 30, loss_streak_trigger: 3, max_correlated_exposure_count: 2, max_open_positions_in_group: 3, default_execution_mode: "paper", position_cap_multiple: 0.9, primary_setup: "breakout_confirmation", primary_regime: "breakout", notes: "" },
  SPY: { name: "SPDR S&P 500 ETF", asset_class: "etf", composite_baseline_prior: 0.717, historical_asset_win_rate: 0.7727, confidence_floor: 0.62, signal_score_floor: 69, risk_per_trade_bp: 80, spread_bps_cap: 12, daily_drawdown_stop_pct: 1.5, cooldown_after_losses_min: 30, loss_streak_trigger: 3, max_correlated_exposure_count: 2, max_open_positions_in_group: 3, default_execution_mode: "paper", position_cap_multiple: 1.15, primary_setup: "breakout_confirmation", primary_regime: "breakout", notes: "Broadest and strongest historical prior; can carry highest position-cap multiple." },
  USDJPY: { name: "USD/JPY", asset_class: "fx", composite_baseline_prior: 0.5262, historical_asset_win_rate: 0.4615, confidence_floor: 0.67, signal_score_floor: 73, risk_per_trade_bp: 40, spread_bps_cap: 10, daily_drawdown_stop_pct: 1.25, cooldown_after_losses_min: 45, loss_streak_trigger: 3, max_correlated_exposure_count: 2, max_open_positions_in_group: 2, default_execution_mode: "paper", position_cap_multiple: 0.85, primary_setup: "breakout_confirmation", primary_regime: "high_volatility", notes: "" },
};

const ASSET_SYMBOLS = ["AAPL", "EURUSD", "GBPUSD", "GLD", "MSFT", "NVDA", "QQQ", "SPY", "USDJPY"] as const;

interface LearningDelta {
  field: keyof AssetBaseline;
  label: string;
  oldValue: number | string;
  newValue: number | string;
  reason: string;
  updatedAt: string;
}

const LEARNING_DELTAS: Partial<Record<string, LearningDelta[]>> = {
  EURUSD: [
    {
      field: "confidence_floor",
      label: "Confidence Floor",
      oldValue: "63%",
      newValue: "65%",
      reason: "15 consecutive sessions with confidence < 64% produced negative edge. Floor raised to improve signal quality gate.",
      updatedAt: "2026-04-25",
    },
    {
      field: "cooldown_after_losses_min",
      label: "Cooldown After Loss",
      oldValue: "30 min",
      newValue: "45 min",
      reason: "Post-loss re-entry within 30 min showed 68% higher false-positive rate during London/NY overlap. Extended to 45 min.",
      updatedAt: "2026-04-24",
    },
  ],
  NVDA: [
    {
      field: "spread_bps_cap",
      label: "Spread Cap",
      oldValue: "18 bps",
      newValue: "20 bps",
      reason: "Average spread widened +2 bps across last 30 earnings-window sessions. Cap adjusted to prevent excess rejections.",
      updatedAt: "2026-04-25",
    },
    {
      field: "risk_per_trade_bp",
      label: "Risk / Trade",
      oldValue: "55 bp",
      newValue: "50 bp",
      reason: "High-beta single-name drawdown events 3× more frequent vs model cluster. Reduced risk allocation per trade.",
      updatedAt: "2026-04-23",
    },
  ],
  SPY: [
    {
      field: "signal_score_floor",
      label: "Signal Score Floor",
      oldValue: "67",
      newValue: "69",
      reason: "Breakout setup false-positive rate increased +12% in low-volatility regime. Score floor tightened to filter weak setups.",
      updatedAt: "2026-04-26",
    },
  ],
  GLD: [
    {
      field: "confidence_floor",
      label: "Confidence Floor",
      oldValue: "64%",
      newValue: "66%",
      reason: "Gold proxy event-driven gaps caused 22% excess drawdown when confidence was 64–65%. Raised floor to reduce exposure during uncertainty.",
      updatedAt: "2026-04-24",
    },
    {
      field: "max_correlated_exposure_count",
      label: "Max Correlated",
      oldValue: "2",
      newValue: "1",
      reason: "Simultaneous GLD + USDJPY exposure during risk-off regimes compounded losses. Correlation limit tightened to 1.",
      updatedAt: "2026-04-22",
    },
  ],
  USDJPY: [
    {
      field: "signal_score_floor",
      label: "Signal Score Floor",
      oldValue: "70",
      newValue: "73",
      reason: "High-volatility regime produces more frequent signal noise around BoJ intervention windows. Score floor raised by +3.",
      updatedAt: "2026-04-25",
    },
  ],
};

function inputStyle(): React.CSSProperties {
  return {
    width: "100%",
    padding: "12px 14px",
    borderRadius: 12,
    border: "1px solid var(--control-border)",
    background: "var(--control-bg)",
    color: "var(--control-text)",
    fontSize: 15,
  };
}

function labelStyle(): React.CSSProperties {
  return {
    display: "grid",
    gap: 8,
    color: "var(--text-body)",
    fontWeight: 600,
  };
}

function buildManualSignal(
  form: RiskFormState,
  baseline: AssetBaseline | null,
  confidence: number,
  signalScore: number,
): SignalResponse {
  return {
    asset: form.asset.toUpperCase(),
    timeframe: form.timeframe,
    direction: form.direction,
    regime: (baseline?.primary_regime as SignalResponse["regime"]) ?? "trend",
    setup_type: (baseline?.primary_setup as SignalResponse["setup_type"]) ?? "trend_pullback",
    entry_zone: [1, 1.01],
    stop_price: 0.99,
    target_price: 1.02,
    confidence,
    horizon_label: "intraday",
    catalyst_type: "none",
    catalyst_score: 0,
    catalyst_summary: "Manual risk evaluation",
    thesis: "Risk evaluation from manual form input.",
    invalidators: ["manual_risk_check"],
    signal_score: signalScore,
    should_trade: form.shouldTrade,
  };
}

function RiskPageContent() {
  const searchParams = useSearchParams();
  const urlAsset = searchParams.get("asset");
  const [form, setForm] = useState<RiskFormState>(initialState);
  const [result, setResult] = useState<RiskDecisionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [opportunities, setOpportunities] = useState<RankedOpportunity[]>([]);
  const [batchResults, setBatchResults] = useState<Array<{ asset: string; score: number; confidence: number; decision: RiskDecisionResponse }>>([]);
  const [batchRunning, setBatchRunning] = useState(false);
  const [expandedDeltas, setExpandedDeltas] = useState<string | null>(null);

  const baseline = useMemo(() => ASSET_BASELINES[form.asset.toUpperCase()] ?? null, [form.asset]);
  const activeDeltas = useMemo(() => LEARNING_DELTAS[form.asset.toUpperCase()] ?? null, [form.asset]);

  const batchSummary = useMemo(() => {
    if (batchResults.length === 0) return null;
    const approved = batchResults.filter((r) => r.decision.approved).length;
    const avgRisk = batchResults.reduce((sum, r) => sum + r.decision.allowed_risk_amount, 0) / batchResults.length;
    return { approved, denied: batchResults.length - approved, total: batchResults.length, avgRisk };
  }, [batchResults]);

  useEffect(() => {
    if (!urlAsset) return;
    setForm((prev) => ({ ...prev, asset: urlAsset.toUpperCase() }));
  }, [urlAsset]);

  useEffect(() => {
    getOpportunities(20)
      .then((res) => setOpportunities(res.items))
      .catch(() => setOpportunities([]));
  }, []);

  useLivePolling(() => {
    getOpportunities(20)
      .then((res) => setOpportunities(res.items))
      .catch(() => setOpportunities([]));
  }, 15000, { enabled: true, runImmediately: false });

  function toSignalDirection(value: string): SignalDirection {
    if (value === "long" || value === "short" || value === "flat") return value;
    return "flat";
  }

  function toSignalFromOpportunity(opp: RankedOpportunity): SignalResponse {
    return {
      asset: opp.asset,
      timeframe: form.timeframe,
      direction: toSignalDirection(opp.direction),
      regime: "trend",
      setup_type: "trend_pullback",
      entry_zone: [opp.entry_low, opp.entry_high],
      stop_price: opp.stop_price,
      target_price: opp.target_price,
      confidence: opp.confidence,
      horizon_label: "intraday",
      catalyst_type: "none",
      catalyst_score: 0,
      catalyst_summary: "Live opportunity snapshot",
      thesis: `Risk evaluation from ranked opportunity (${opp.setup_type})`,
      invalidators: ["opportunity_snapshot"],
      signal_score: opp.score,
      should_trade: true,
    };
  }

  async function runBatchRiskOnOpportunities() {
    if (batchRunning || opportunities.length === 0) return;
    setBatchRunning(true);
    setError(null);

    const spreadBps = Number(form.spreadBps);
    const dailyDrawdownPct = Number(form.dailyDrawdownPct);
    const consecutiveLosses = Number(form.consecutiveLosses);
    const accountEquity = Number(form.accountEquity);
    const correlatedExposureCount = Number(form.correlatedExposureCount);
    const openPositionsCount = Number(form.openPositionsCount);
    const minutesSinceLastLoss = form.minutesSinceLastLoss === "" ? null : Number(form.minutesSinceLastLoss);

    const rows: Array<{ asset: string; score: number; confidence: number; decision: RiskDecisionResponse }> = [];
    for (const opp of opportunities) {
      try {
        const decision = await evaluateRisk({
          signal: toSignalFromOpportunity(opp),
          risk_context: {
            spread_bps: spreadBps,
            daily_drawdown_pct: dailyDrawdownPct,
            consecutive_losses: consecutiveLosses,
            minutes_since_last_loss: minutesSinceLastLoss,
            correlated_exposure_count: correlatedExposureCount,
            open_positions_count: openPositionsCount,
            market_quality_flag: form.marketQualityFlag,
            session_allowed: form.sessionAllowed,
            kill_switch_active: form.killSwitchActive,
            account_equity: accountEquity,
            requested_execution_mode: form.requestedExecutionMode,
          },
        });
        rows.push({ asset: opp.asset, score: opp.score, confidence: opp.confidence, decision });
      } catch {
        // Skip rows that fail server-side validation.
      }
    }

    setBatchResults(rows);
    setBatchRunning(false);
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const confidence = Number(form.confidence);
    const signalScore = Number(form.signalScore);
    const spreadBps = Number(form.spreadBps);
    const dailyDrawdownPct = Number(form.dailyDrawdownPct);
    const consecutiveLosses = Number(form.consecutiveLosses);
    const accountEquity = Number(form.accountEquity);

    if (!Number.isFinite(confidence) || confidence < 0 || confidence > 1) {
      setError("Confidence must be a valid number between 0 and 1.");
      return;
    }
    if (!Number.isFinite(signalScore) || signalScore < 0 || signalScore > 100) {
      setError("Signal score must be a valid number between 0 and 100.");
      return;
    }
    if (!Number.isFinite(spreadBps) || spreadBps < 0) {
      setError("Spread bps must be a valid number and >= 0.");
      return;
    }
    if (!Number.isFinite(dailyDrawdownPct) || dailyDrawdownPct < 0) {
      setError("Daily drawdown % must be a valid number and >= 0.");
      return;
    }
    if (!Number.isFinite(consecutiveLosses) || consecutiveLosses < 0) {
      setError("Consecutive losses must be a valid number and >= 0.");
      return;
    }
    if (!Number.isFinite(accountEquity) || accountEquity < 0) {
      setError("Account equity must be a valid number and >= 0.");
      return;
    }
    const correlatedExposureCount = Number(form.correlatedExposureCount);
    if (!Number.isFinite(correlatedExposureCount) || correlatedExposureCount < 0) {
      setError("Correlated exposure count must be a valid number and >= 0.");
      return;
    }
    const openPositionsCount = Number(form.openPositionsCount);
    if (!Number.isFinite(openPositionsCount) || openPositionsCount < 0) {
      setError("Open positions count must be a valid number and >= 0.");
      return;
    }
    const minutesSinceLastLoss = form.minutesSinceLastLoss === "" ? null : Number(form.minutesSinceLastLoss);
    if (minutesSinceLastLoss !== null && (!Number.isFinite(minutesSinceLastLoss) || minutesSinceLastLoss < 0)) {
      setError("Minutes since last loss must be a valid number and >= 0.");
      return;
    }

    setIsSubmitting(true);

    try {
      const selectedOpportunity = opportunities.find((op) => op.asset.toUpperCase() === form.asset.toUpperCase());
      const signal = selectedOpportunity
        ? {
            ...toSignalFromOpportunity(selectedOpportunity),
            confidence,
            signal_score: signalScore,
            should_trade: form.shouldTrade,
            direction: form.direction,
          }
        : buildManualSignal(form, baseline, confidence, signalScore);

      const response = await evaluateRisk({
        signal,
        risk_context: {
          spread_bps: spreadBps,
          daily_drawdown_pct: dailyDrawdownPct,
          consecutive_losses: consecutiveLosses,
          minutes_since_last_loss: minutesSinceLastLoss,
          correlated_exposure_count: correlatedExposureCount,
          open_positions_count: openPositionsCount,
          market_quality_flag: form.marketQualityFlag,
          session_allowed: form.sessionAllowed,
          kill_switch_active: form.killSwitchActive,
          account_equity: accountEquity,
          requested_execution_mode: form.requestedExecutionMode,
        },
      });
      setResult(response);
    } catch (submitError) {
      setResult(null);
      setError(submitError instanceof Error ? submitError.message : "Unknown request failure");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        padding: "32px 20px 64px",
        background: "var(--app-shell-bg)",
      }}
    >
      <div style={{ maxWidth: 980, margin: "0 auto", display: "grid", gap: 24 }}>

        {/* ── Asset Matrix Table ──────────────────────────────────────────── */}
        <section className={styles.panel}>
          <div className={styles.panelHeader}>
            <h3 className={styles.panelTitle}>Asset Risk Matrix</h3>
            <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
              Select an asset to load its baseline into the form
            </span>
          </div>
          <div className={styles.tableWrap}>
            <table className={styles.riskTable}>
              <thead>
                <tr>
                  <th>Asset</th>
                  <th>Class</th>
                  <th>Win Rate</th>
                  <th>Composite Prior</th>
                  <th>Conf. Floor</th>
                  <th>Score Floor</th>
                  <th>Spread Cap</th>
                  <th>Drawdown Stop</th>
                  <th>Mode</th>
                  <th style={{ textAlign: "center" }}>Updates</th>
                </tr>
              </thead>
              <tbody>
                {ASSET_SYMBOLS.map((sym) => {
                  const b = ASSET_BASELINES[sym];
                  const deltas = LEARNING_DELTAS[sym];
                  const isActive = form.asset.toUpperCase() === sym;
                  return (
                    <tr
                      key={sym}
                      className={isActive ? styles.matrixRowActive : styles.matrixRow}
                      onClick={() => setForm((prev) => ({ ...prev, asset: sym }))}
                    >
                      <td>
                        <div className={styles.matrixAssetCell}>
                          <span className={styles.matrixAssetSymbol}>{sym}</span>
                          <span className={styles.matrixAssetName}>{b.name}</span>
                        </div>
                      </td>
                      <td className={styles.tdMuted} style={{ textTransform: "capitalize" }}>{b.asset_class.replace(/_/g, " ")}</td>
                      <td style={{ color: b.historical_asset_win_rate >= 0.6 ? "var(--state-success)" : b.historical_asset_win_rate >= 0.5 ? "var(--state-warning)" : "var(--state-danger)", fontWeight: 700 }}>
                        {(b.historical_asset_win_rate * 100).toFixed(1)}%
                      </td>
                      <td style={{ color: b.composite_baseline_prior >= 0.6 ? "var(--state-success)" : "var(--text-body)" }}>
                        {(b.composite_baseline_prior * 100).toFixed(1)}%
                      </td>
                      <td>{(b.confidence_floor * 100).toFixed(0)}%</td>
                      <td>{b.signal_score_floor}</td>
                      <td>{b.spread_bps_cap} bps</td>
                      <td>{b.daily_drawdown_stop_pct}%</td>
                      <td className={styles.tdMuted} style={{ textTransform: "capitalize" }}>{b.default_execution_mode.replace(/_/g, " ")}</td>
                      <td style={{ textAlign: "center" }}>
                        {deltas && deltas.length > 0 ? (
                          <span className={styles.learningBadge}>
                            <span className={styles.learningPulse} />
                            {deltas.length} update{deltas.length > 1 ? "s" : ""}
                          </span>
                        ) : (
                          <span className={styles.tdMuted} style={{ fontSize: 11 }}>—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>

        <FormSection title="Risk" description="Evaluate risk decisions and compare outcomes across multiple assets.">
          <form onSubmit={handleSubmit} style={{ display: "grid", gap: 16 }}>
            <label style={labelStyle()}>
              Asset
              <input style={inputStyle()} value={form.asset} onChange={(event) => setForm({ ...form, asset: event.target.value })} />
            </label>

            <label style={labelStyle()}>
              Timeframe
              <select
                style={inputStyle()}
                value={form.timeframe}
                onChange={(event) => setForm({ ...form, timeframe: event.target.value as Timeframe })}
              >
                <option value="15m">15m</option>
                <option value="1h">1h</option>
                <option value="4h">4h</option>
                <option value="1d">1d</option>
              </select>
            </label>

            <label style={labelStyle()}>
              Direction
              <select
                style={inputStyle()}
                value={form.direction}
                onChange={(event) => setForm({ ...form, direction: event.target.value as SignalDirection })}
              >
                <option value="long">long</option>
                <option value="short">short</option>
                <option value="flat">flat</option>
              </select>
            </label>

            <label style={{ ...labelStyle(), gridTemplateColumns: "auto 1fr", alignItems: "center" }}>
              <input
                type="checkbox"
                checked={form.shouldTrade}
                onChange={(event) => setForm({ ...form, shouldTrade: event.target.checked })}
              />
              <LearnTooltip explain={{ beginner: "Whether the model recommends trading this signal. Uncheck to test what happens when the AI says don't trade.", intermediate: "signal.should_trade: false adds signal_not_actionable to rejection reasons.", experienced: "should_trade=false is the primary gate. Overrides confidence/score checks.", expert: "should_trade: boolean. False → signal_not_actionable regardless of score/confidence." }}>Signal should_trade</LearnTooltip>
            </label>

            <label style={labelStyle()}>
              <LearnTooltip explain={{ beginner: "Confidence is how certain the model is about the signal (0 = no confidence, 1 = maximum confidence). Higher confidence increases the chance of risk approval.", intermediate: "Model confidence score (0–1). Risk gate requires confidence ≥ minimum threshold.", experienced: "Classifier output probability. Below 0.5 is typically blocked by risk.", expert: "P(signal | features). Threshold-gated in risk evaluation pipeline." }}>Confidence</LearnTooltip>
              <input
                style={inputStyle()}
                inputMode="decimal"
                min={0}
                max={1}
                step="any"
                value={form.confidence}
                onChange={(event) => setForm({ ...form, confidence: event.target.value })}
              />
              <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text-muted)" }}>Enter a value from 0 to 1</span>
            </label>

            <label style={labelStyle()}>
              <LearnTooltip explain={{ beginner: "Signal Score is a 0–100 quality score. Higher means a better signal. Risk evaluation requires a minimum score before allowing a trade.", intermediate: "Composite signal quality score 0–100. Risk gate typically requires ≥60.", experienced: "Normalised signal strength score. Risk threshold: ≥60 for paper, ≥70 for live.", expert: "Weighted composite: regime_score × setup_score × momentum. Risk floor: depends on execution_mode." }}>Signal score</LearnTooltip>
              <input
                style={inputStyle()}
                inputMode="decimal"
                min={0}
                max={100}
                step="any"
                value={form.signalScore}
                onChange={(event) => setForm({ ...form, signalScore: event.target.value })}
              />
              <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text-muted)" }}>Enter a value from 0 to 100</span>
            </label>

            <label style={labelStyle()}>
              <LearnTooltip explain={{ beginner: "Spread is the difference between the buy and sell price, measured in basis points (1 bps = 0.01%). High spread = more cost to enter the trade.", intermediate: "Bid-ask spread in basis points (bps). 1 bps = 0.0001 for forex. High spread reduces expected profit.", experienced: "Spread cost in bps. At 10 bps on EURUSD ≈ 1 pip. Affects net P&L and risk approval.", expert: "spread_bps: transaction cost proxy. Subtracted from expected value in risk gate." }}>Spread bps</LearnTooltip>
              <input
                style={inputStyle()}
                inputMode="decimal"
                min={0}
                step="any"
                value={form.spreadBps}
                onChange={(event) => setForm({ ...form, spreadBps: event.target.value })}
              />
              <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text-muted)" }}>Number, 0 or more</span>
            </label>

            <label style={labelStyle()}>
              <LearnTooltip explain={{ beginner: "Daily drawdown is how much of your account you've lost today as a percentage. If it exceeds the risk limit, no new trades are allowed.", intermediate: "Daily P&L drawdown as % of account equity. Risk gate blocks new trades if above the daily loss limit.", experienced: "daily_drawdown_pct: realised P&L loss today / equity. Triggers risk block if exceeds max_daily_dd.", expert: "daily_drawdown_pct = abs(daily_pnl) / account_equity × 100. Kill-switch if ≥ max_daily_dd threshold." }}>Daily drawdown %</LearnTooltip>
              <input
                style={inputStyle()}
                inputMode="decimal"
                min={0}
                step="any"
                value={form.dailyDrawdownPct}
                onChange={(event) => setForm({ ...form, dailyDrawdownPct: event.target.value })}
              />
              <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text-muted)" }}>Number, 0 or more</span>
            </label>

            <label style={labelStyle()}>
              <LearnTooltip explain={{ beginner: "How many trades in a row have been losses. Too many consecutive losses triggers a circuit breaker — the system stops trading to protect your account.", intermediate: "Count of sequential losing trades. Risk gate enforces a max_consecutive_losses circuit breaker.", experienced: "Consecutive loss counter. Triggers cooldown / trade pause if ≥ threshold (typically 3–5).", expert: "consecutive_losses: loss streak counter. Circuit breaker activates at configured max." }}>Consecutive losses</LearnTooltip>
              <input
                style={inputStyle()}
                inputMode="numeric"
                min={0}
                step={1}
                value={form.consecutiveLosses}
                onChange={(event) => setForm({ ...form, consecutiveLosses: event.target.value })}
              />
              <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text-muted)" }}>Whole number, 0 or more</span>
            </label>

            <label style={labelStyle()}>
              <LearnTooltip explain={{ beginner: "How many minutes since the last losing trade. The risk system may enforce a cooldown period to prevent trading immediately after a loss.", intermediate: "Minutes elapsed since the last losing trade. Below cooldown threshold = trading paused.", experienced: "minutes_since_last_loss: used to enforce post-loss cooldown window.", expert: "minutes_since_last_loss: compared to cooldown_minutes_after_loss in risk profile. Leave blank = no cooldown." }}>Minutes since last loss</LearnTooltip>
              <input
                style={inputStyle()}
                inputMode="numeric"
                min={0}
                step={1}
                placeholder="Leave blank if not applicable"
                value={form.minutesSinceLastLoss}
                onChange={(event) => setForm({ ...form, minutesSinceLastLoss: event.target.value })}
              />
              <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text-muted)" }}>Whole number, or leave blank</span>
            </label>

            <label style={labelStyle()}>
              <LearnTooltip explain={{ beginner: "How many correlated positions are currently open. Too many similar positions means too much risk is concentrated in one area.", intermediate: "Count of open positions in correlated assets. Exceeding the cap triggers a block.", experienced: "correlated_exposure_count: used to cap sector/pair concentration risk.", expert: "correlated_exposure_count: checked against max_correlated_exposure in risk profile." }}>Correlated exposure count</LearnTooltip>
              <input
                style={inputStyle()}
                inputMode="numeric"
                min={0}
                step={1}
                value={form.correlatedExposureCount}
                onChange={(event) => setForm({ ...form, correlatedExposureCount: event.target.value })}
              />
              <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text-muted)" }}>Whole number, 0 or more</span>
            </label>

            <label style={labelStyle()}>
              <LearnTooltip explain={{ beginner: "How many trades are currently open. The system limits open positions to prevent overexposure.", intermediate: "Total count of open positions. The risk gate blocks new trades beyond the max.", experienced: "open_positions_count: checked against _MAX_OPEN_POSITIONS_MVP (6).", expert: "open_positions_count ≥ _MAX_OPEN_POSITIONS_MVP → max_open_positions_exceeded block." }}>Open positions count</LearnTooltip>
              <input
                style={inputStyle()}
                inputMode="numeric"
                min={0}
                step={1}
                value={form.openPositionsCount}
                onChange={(event) => setForm({ ...form, openPositionsCount: event.target.value })}
              />
              <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text-muted)" }}>Whole number, 0 or more</span>
            </label>

            <div data-rs="risk-flags" style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
              <label style={{ ...labelStyle(), gridTemplateColumns: "auto 1fr", alignItems: "center", gap: 8, color: "var(--text-body)", fontWeight: 600, fontSize: 13 }}>
                <input
                  type="checkbox"
                  checked={form.shouldTrade}
                  onChange={(event) => setForm({ ...form, shouldTrade: event.target.checked })}
                />
                <span>
                  <LearnTooltip explain={{ beginner: "Whether the AI model recommends trading this signal. Uncheck to test what happens when the model says don't trade.", intermediate: "signal.should_trade: if false, risk gate adds signal_not_actionable rejection.", experienced: "should_trade=false short-circuits risk approval regardless of other parameters.", expert: "should_trade: boolean gate. False → signal_not_actionable in blocked_reasons." }}>Signal should trade</LearnTooltip>
                </span>
              </label>

              <label style={{ ...labelStyle(), gridTemplateColumns: "auto 1fr", alignItems: "center", gap: 8, color: "var(--text-body)", fontWeight: 600, fontSize: 13 }}>
                <input
                  type="checkbox"
                  checked={form.marketQualityFlag}
                  onChange={(event) => setForm({ ...form, marketQualityFlag: event.target.checked })}
                />
                <span>
                  <LearnTooltip explain={{ beginner: "Market quality is an indicator of whether conditions are good enough to trade. Uncheck when market conditions degrade.", intermediate: "market_quality_flag=false adds market_quality_bad rejection.", experienced: "market_quality_flag: derived from spread, volatility, liquidity checks.", expert: "market_quality_flag: boolean. False → market_quality_bad in blocked_reasons." }}>Market quality OK</LearnTooltip>
                </span>
              </label>

              <label style={{ ...labelStyle(), gridTemplateColumns: "auto 1fr", alignItems: "center", gap: 8, color: "var(--text-body)", fontWeight: 600, fontSize: 13 }}>
                <input
                  type="checkbox"
                  checked={form.sessionAllowed}
                  onChange={(event) => setForm({ ...form, sessionAllowed: event.target.checked })}
                />
                <span>
                  <LearnTooltip explain={{ beginner: "Session allowed means trading is permitted in the current market session (e.g. London/NY open). Uncheck outside approved hours.", intermediate: "session_allowed=false adds session_not_allowed rejection.", experienced: "session_allowed: checked against trading-hours config for the asset.", expert: "session_allowed: boolean. False → session_not_allowed in blocked_reasons." }}>Session allowed</LearnTooltip>
                </span>
              </label>

              <label style={{ ...labelStyle(), gridTemplateColumns: "auto 1fr", alignItems: "center", gap: 8, color: "var(--text-body)", fontWeight: 600, fontSize: 13 }}>
                <input
                  type="checkbox"
                  checked={form.killSwitchActive}
                  onChange={(event) => setForm({ ...form, killSwitchActive: event.target.checked })}
                />
                <span>
                  <LearnTooltip explain={{ beginner: "The kill switch is an emergency stop — when active, all new trading is halted immediately.", intermediate: "kill_switch_active=true adds kill_switch_active rejection regardless of other inputs.", experienced: "Kill switch is the highest-priority block. Overrides all other risk checks.", expert: "kill_switch_active: boolean. True → kill_switch_active in blocked_reasons before any other check." }}>Kill switch active</LearnTooltip>
                </span>
              </label>
            </div>

            <label style={labelStyle()}>
              <LearnTooltip explain={{ beginner: "Account equity is the total value of your trading account. It's used to calculate how much you should risk per trade.", intermediate: "Total account equity in base currency. Used to compute position size as % of equity.", experienced: "account_equity: base for position sizing. risk_notional = equity × risk_pct_per_trade.", expert: "account_equity: denominator for Kelly / fixed-fraction position sizing." }}>Account equity</LearnTooltip>
              <input
                style={inputStyle()}
                inputMode="decimal"
                min={0}
                step="any"
                value={form.accountEquity}
                onChange={(event) => setForm({ ...form, accountEquity: event.target.value })}
              />
              <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text-muted)" }}>Number, 0 or more</span>
            </label>

            <label style={labelStyle()}>
              <LearnTooltip explain={{ beginner: "Execution mode controls order routing. Paper uses your broker paper account. Confirm Live requires manual approval before live submission. Auto Live is fully automated live routing.", intermediate: "paper: broker paper account. confirm_live: live with manual approval step. auto_live: fully automated live execution.", experienced: "Execution mode determines risk gate strictness. auto_live requires highest signal_score and confidence thresholds.", expert: "execution_mode: paper | confirm_live | auto_live. Determines risk gate thresholds and order routing." }}>Requested execution mode</LearnTooltip>
              <select
                style={inputStyle()}
                value={form.requestedExecutionMode}
                onChange={(event) => setForm({ ...form, requestedExecutionMode: event.target.value as ExecutionMode })}
              >
                <option value="paper">paper</option>
                <option value="confirm_live">confirm_live</option>
                <option value="auto_live">auto_live</option>
              </select>
            </label>

            <button
              type="submit"
              disabled={isSubmitting}
              style={{
                border: 0,
                borderRadius: 14,
                padding: "14px 18px",
                background: isSubmitting ? "color-mix(in oklab, var(--state-info) 34%, var(--surface-soft))" : "var(--state-info)",
                color: "var(--text-strong)",
                fontSize: 15,
                fontWeight: 700,
                cursor: isSubmitting ? "not-allowed" : "pointer",
              }}
            >
              {isSubmitting ? "Evaluating..." : "Evaluate risk"}
            </button>

            {error ? (
              <div style={{ padding: 14, borderRadius: 12, border: "1px solid var(--state-warning-border)", background: "var(--state-warning-soft)", color: "var(--state-warning)" }}>
                {error}
              </div>
            ) : null}
          </form>
        </FormSection>

        {/* ── Asset Baseline Strip ────────────────────────────────────────── */}
        {baseline ? (
          <section className={styles.panel}>
            <div className={styles.panelHeader}>
              <h3 className={styles.panelTitle}>
                {baseline.name} — Asset Baseline
              </h3>
              <span style={{ fontSize: 12, color: "var(--text-muted)", fontWeight: 600 }}>
                {baseline.asset_class.replace("_", " ")} · {baseline.primary_setup.replace(/_/g, " ")} · {baseline.primary_regime.replace(/_/g, " ")}
              </span>
            </div>
            <div className={styles.kpiGrid}>
              <div className={styles.kpiCard}>
                <div className={styles.kpiLabel}>Historical Win Rate</div>
                <div className={styles.kpiValue} style={{ color: baseline.historical_asset_win_rate >= 0.6 ? "var(--state-success)" : baseline.historical_asset_win_rate >= 0.5 ? "var(--state-warning)" : "var(--state-danger)" }}>
                  {(baseline.historical_asset_win_rate * 100).toFixed(1)}%
                </div>
              </div>
              <div className={styles.kpiCard}>
                <div className={styles.kpiLabel}>Composite Prior</div>
                <div className={styles.kpiValue} style={{ color: baseline.composite_baseline_prior >= 0.6 ? "var(--state-success)" : "var(--state-warning)" }}>
                  {(baseline.composite_baseline_prior * 100).toFixed(1)}%
                </div>
              </div>
              <div className={styles.kpiCard}>
                <div className={styles.kpiLabel}>Confidence Floor</div>
                <div className={styles.kpiValue}>{(baseline.confidence_floor * 100).toFixed(0)}%</div>
              </div>
              <div className={styles.kpiCard}>
                <div className={styles.kpiLabel}>Score Floor</div>
                <div className={styles.kpiValue}>{baseline.signal_score_floor}</div>
              </div>
              <div className={styles.kpiCard}>
                <div className={styles.kpiLabel}>Risk / Trade</div>
                <div className={styles.kpiValue}>{baseline.risk_per_trade_bp} bp</div>
              </div>
              <div className={styles.kpiCard}>
                <div className={styles.kpiLabel}>Spread Cap</div>
                <div className={styles.kpiValue}>{baseline.spread_bps_cap} bps</div>
              </div>
              <div className={styles.kpiCard}>
                <div className={styles.kpiLabel}>Drawdown Stop</div>
                <div className={styles.kpiValue}>{baseline.daily_drawdown_stop_pct}%</div>
              </div>
              <div className={styles.kpiCard}>
                <div className={styles.kpiLabel}>Loss Streak Limit</div>
                <div className={styles.kpiValue}>{baseline.loss_streak_trigger} losses</div>
              </div>
              <div className={styles.kpiCard}>
                <div className={styles.kpiLabel}>Cooldown After Loss</div>
                <div className={styles.kpiValue}>{baseline.cooldown_after_losses_min} min</div>
              </div>
              <div className={styles.kpiCard}>
                <div className={styles.kpiLabel}>Max Correlated</div>
                <div className={styles.kpiValue}>{baseline.max_correlated_exposure_count}</div>
              </div>
              <div className={styles.kpiCard}>
                <div className={styles.kpiLabel}>Pos Cap ×</div>
                <div className={styles.kpiValue}>{baseline.position_cap_multiple}×</div>
              </div>
              <div className={styles.kpiCard}>
                <div className={styles.kpiLabel}>Default Mode</div>
                <div className={styles.kpiValue} style={{ textTransform: "capitalize", fontSize: 13 }}>{baseline.default_execution_mode.replace(/_/g, " ")}</div>
              </div>
            </div>
            {baseline.notes ? (
              <p style={{ margin: 0, fontSize: 12, color: "var(--text-muted)", fontStyle: "italic" }}>{baseline.notes}</p>
            ) : null}

            {/* ── Learning Model Updates ──────────────────────────────────── */}
            {activeDeltas && activeDeltas.length > 0 ? (
              <div className={styles.learningPanel}>
                <button
                  type="button"
                  className={styles.learningHeader}
                  onClick={() => setExpandedDeltas(expandedDeltas === form.asset ? null : form.asset)}
                >
                  <span className={styles.learningHeaderLeft}>
                    <span className={styles.learningPulse} />
                    <span className={styles.learningTitle}>Learning Model Updates</span>
                    <span className={styles.learningCount}>{activeDeltas.length} parameter{activeDeltas.length > 1 ? "s" : ""} updated</span>
                  </span>
                  <span className={styles.learningChevron}>{expandedDeltas === form.asset ? "▲" : "▼"}</span>
                </button>
                {expandedDeltas === form.asset ? (
                  <div className={styles.learningBody}>
                    {activeDeltas.map((delta, idx) => (
                      <div key={idx} className={styles.learningDeltaRow}>
                        <div className={styles.learningDeltaHeader}>
                          <span className={styles.learningDeltaField}>{delta.label}</span>
                          <span className={styles.learningDeltaChange}>
                            <span className={styles.learningOldVal}>{delta.oldValue}</span>
                            <span className={styles.learningArrow}>→</span>
                            <span className={styles.learningNewVal}>{delta.newValue}</span>
                          </span>
                          <span className={styles.learningDate}>{delta.updatedAt}</span>
                        </div>
                        <p className={styles.learningReason}>{delta.reason}</p>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : null}
          </section>
        ) : null}

        {/* ── Risk Decision Result ─────────────────────────────────────────── */}
        {result ? (
          <section className={styles.panel}>
            {/* Decision Banner */}
            <div className={`${styles.decisionBanner} ${result.approved ? styles.decisionBannerApproved : styles.decisionBannerDenied}`}>
              <div className={styles.decisionBadge}>
                <span className={styles.decisionIcon}>{result.approved ? "✓" : "✗"}</span>
                <span className={`${styles.decisionLabel} ${result.approved ? styles.decisionLabelApproved : styles.decisionLabelDenied}`}>
                  {result.approved ? "APPROVED" : "DENIED"}
                </span>
              </div>
              <div className={styles.decisionMeta}>
                <LearnTooltip
                  explain={{
                    beginner: "Approved means all risk checks passed. Denied means one or more limits were breached.",
                    intermediate: "Risk gate: passes when signal quality, drawdown, spread, and consecutive losses are all within limits.",
                    experienced: "risk_decision.approved: all gate checks pass — signal_score, confidence, drawdown, spread, consecutive_losses.",
                    expert: "risk_decision.approved: boolean AND of all individual gate conditions.",
                  }}
                  placement="left"
                >
                  <span style={{ fontSize: 12, color: result.approved ? "var(--state-success)" : "var(--state-danger)", fontWeight: 600 }}>
                    {result.approved ? "All gates passed" : "One or more gates failed"}
                  </span>
                </LearnTooltip>
              </div>
            </div>

            {/* KPI row */}
            <div className={styles.kpiGrid}>
              <div className={styles.kpiCard}>
                <div className={styles.kpiLabel}>
                  <LearnTooltip explain={{ beginner: "How much capital the risk system allows for this trade.", intermediate: "Allowed risk amount in dollars based on account equity and position sizing.", experienced: "allowed_risk_amount = account_equity × position_size_pct.", expert: "allowed_risk_amount: float. Product of account equity and resolved position_size_pct." }}>
                    Allowed Risk $
                  </LearnTooltip>
                </div>
                <div className={styles.kpiValue} style={{ color: "var(--state-success)" }}>
                  ${result.allowed_risk_amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
              </div>

              <div className={styles.kpiCard}>
                <div className={styles.kpiLabel}>
                  <LearnTooltip explain={{ beginner: "The execution mode granted by risk (may be downgraded from what you requested).", intermediate: "Approved execution mode; may be paper if live thresholds not met.", experienced: "selected_execution_mode: approved mode after gate evaluation.", expert: "selected_execution_mode: may downgrade auto_live → confirm_live → paper." }}>
                    Execution Mode
                  </LearnTooltip>
                </div>
                <div className={styles.kpiValue} style={{ fontSize: 13, textTransform: "capitalize" }}>
                  {(result.selected_execution_mode ?? result.execution_mode ?? "—").replace(/_/g, " ")}
                </div>
              </div>

              {result.position_size_pct !== undefined && result.position_size_pct !== null ? (
                <div className={styles.kpiCard}>
                  <div className={styles.kpiLabel}>
                    <LearnTooltip explain={{ beginner: "How much of your account to risk as a percentage.", intermediate: "Position size % of account equity.", experienced: "position_size_pct: derived from signal quality and risk parameters.", expert: "position_size_pct = f(confidence, signal_score, account_equity, max_risk_pct)." }}>
                      Position Size %
                    </LearnTooltip>
                  </div>
                  <div className={styles.kpiValue} style={{ color: "var(--state-success)" }}>
                    {(result.position_size_pct * 100).toFixed(2)}%
                  </div>
                </div>
              ) : null}

              {result.risk_score !== undefined && result.risk_score !== null ? (
                <div className={styles.kpiCard}>
                  <div className={styles.kpiLabel}>
                    <LearnTooltip explain={{ beginner: "Composite risk score 0–100. Higher = riskier.", intermediate: "Aggregated risk metric from spread, drawdown, consecutive losses, signal quality.", experienced: "risk_score: weighted sum of risk factor violations.", expert: "risk_score: higher = closer to rejection threshold." }}>
                      Risk Score
                    </LearnTooltip>
                  </div>
                  <div className={styles.riskScoreWrap}>
                    <div className={styles.kpiValue} style={{ color: result.risk_score >= 70 ? "var(--state-danger)" : result.risk_score >= 40 ? "var(--state-warning)" : "var(--state-success)" }}>
                      {result.risk_score}
                    </div>
                    <div className={styles.riskScoreBar}>
                      <div
                        className={`${styles.riskScoreFill} ${result.risk_score >= 70 ? styles.riskScoreHigh : result.risk_score >= 40 ? styles.riskScoreMid : styles.riskScoreLow}`}
                        style={{ width: `${result.risk_score}%` }}
                      />
                    </div>
                  </div>
                </div>
              ) : null}

              {/* Gate checks vs baseline */}
              {baseline ? (
                <>
                  <div className={styles.kpiCard}>
                    <div className={styles.kpiLabel}>Confidence vs Floor</div>
                    <div className={styles.kpiValue} style={{ color: Number(form.confidence) >= baseline.confidence_floor ? "var(--state-success)" : "var(--state-danger)" }}>
                      {(Number(form.confidence) * 100).toFixed(0)}% <span style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 500 }}>floor {(baseline.confidence_floor * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                  <div className={styles.kpiCard}>
                    <div className={styles.kpiLabel}>Score vs Floor</div>
                    <div className={styles.kpiValue} style={{ color: Number(form.signalScore) >= baseline.signal_score_floor ? "var(--state-success)" : "var(--state-danger)" }}>
                      {form.signalScore} <span style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 500 }}>floor {baseline.signal_score_floor}</span>
                    </div>
                  </div>
                  <div className={styles.kpiCard}>
                    <div className={styles.kpiLabel}>Spread vs Cap</div>
                    <div className={styles.kpiValue} style={{ color: Number(form.spreadBps) <= baseline.spread_bps_cap ? "var(--state-success)" : "var(--state-danger)" }}>
                      {form.spreadBps} bps <span style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 500 }}>cap {baseline.spread_bps_cap}</span>
                    </div>
                  </div>
                </>
              ) : null}
            </div>

            {/* Gate checklist */}
            {baseline ? (
              <div>
                <div className={styles.kpiLabel} style={{ marginBottom: 8 }}>Gate Checks vs Baseline</div>
                <div className={styles.gateGrid}>
                  {[
                    { label: "Confidence", pass: Number(form.confidence) >= baseline.confidence_floor, warn: false },
                    { label: "Signal Score", pass: Number(form.signalScore) >= baseline.signal_score_floor, warn: false },
                    { label: "Spread BPS", pass: Number(form.spreadBps) <= baseline.spread_bps_cap, warn: false },
                    { label: "Drawdown", pass: Number(form.dailyDrawdownPct) <= baseline.daily_drawdown_stop_pct, warn: false },
                    { label: "Loss Streak", pass: Number(form.consecutiveLosses) < baseline.loss_streak_trigger, warn: Number(form.consecutiveLosses) === baseline.loss_streak_trigger - 1 },
                    { label: "Correlated", pass: Number(form.correlatedExposureCount) <= baseline.max_correlated_exposure_count, warn: false },
                    { label: "Kill Switch", pass: !form.killSwitchActive, warn: false },
                    { label: "Session", pass: form.sessionAllowed, warn: false },
                    { label: "Market Quality", pass: form.marketQualityFlag, warn: false },
                  ].map((gate) => (
                    <div key={gate.label} className={styles.gateItem}>
                      <span className={styles.gateLabel}>{gate.label}</span>
                      <span className={gate.pass ? styles.gateBadgePass : gate.warn ? styles.gateBadgeWarn : styles.gateBadgeFail}>
                        {gate.pass ? "PASS" : gate.warn ? "WARN" : "FAIL"}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            {/* Blocked reasons pills */}
            {result.blocked_reasons.length > 0 || (result.rejection_reasons && result.rejection_reasons.length > 0) ? (
              <div className={styles.reasonsBlock}>
                <div className={styles.reasonsTitle}>
                  <LearnTooltip explain={{ beginner: "Which specific risk checks failed and blocked this trade.", intermediate: "Individual gate failures that caused the denial.", experienced: "Rejection reason codes from failed gate checks.", expert: "rejection_reasons[]: array of failed gate check identifiers." }}>
                    Blocked Reasons
                  </LearnTooltip>
                </div>
                <div className={styles.blockedPills}>
                  {[...result.blocked_reasons, ...(result.rejection_reasons ?? [])].map((reason) => (
                    <span key={reason} className={styles.blockedPill}>{reason.replace(/_/g, " ")}</span>
                  ))}
                </div>
              </div>
            ) : null}

            {result.notes && result.notes.length > 0 ? (
              <div className={styles.notesBlock}>
                <div className={styles.notesTitle}>Notes</div>
                <ul className={styles.notesList}>
                  {result.notes.map((note) => (
                    <li key={note} className={styles.notesItem}>{note}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </section>
        ) : null}

        <section className={styles.panel}>
          <div className={styles.panelHeader}>
            <h3 className={styles.panelTitle}>Multi-Asset Risk Table</h3>
            <button
              type="button"
              onClick={() => { void runBatchRiskOnOpportunities(); }}
              disabled={batchRunning || opportunities.length === 0}
              style={{
                border: 0,
                borderRadius: 12,
                padding: "10px 14px",
                background: batchRunning ? "color-mix(in oklab, var(--state-info) 34%, var(--surface-soft))" : "var(--state-info)",
                color: "var(--text-strong)",
                fontSize: 13,
                fontWeight: 700,
                cursor: batchRunning ? "not-allowed" : "pointer",
              }}
            >
              {batchRunning ? "Evaluating..." : `Evaluate ${opportunities.length} opportunities`}
            </button>
          </div>

          {batchSummary ? (
            <div className={styles.batchSummary}>
              <span><span className={styles.batchApproveCount}>{batchSummary.approved}</span> approved</span>
              <span className={styles.batchDivider}>·</span>
              <span><span className={styles.batchDenyCount}>{batchSummary.denied}</span> denied</span>
              <span className={styles.batchDivider}>·</span>
              <span>{batchSummary.total} evaluated</span>
              <span className={styles.batchDivider}>·</span>
              <span style={{ color: "var(--text-muted)" }}>avg allowed risk <strong style={{ color: "var(--text-body)" }}>${batchSummary.avgRisk.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong></span>
            </div>
          ) : null}

          {batchResults.length === 0 ? (
            <p className={styles.emptyMsg}>Run batch risk to populate per-asset decisions from your latest opportunity list.</p>
          ) : (
            <div className={styles.tableWrap}>
              <table className={styles.riskTable}>
                <thead>
                  <tr>
                    <th>Asset</th>
                    <th>Score</th>
                    <th>Confidence</th>
                    <th>Approved</th>
                    <th>Risk $</th>
                    <th>Execution Mode</th>
                    <th>Blocked Reasons</th>
                  </tr>
                </thead>
                <tbody>
                  {batchResults.map((row) => {
                    const rowBaseline = ASSET_BASELINES[row.asset];
                    return (
                      <tr key={row.asset}>
                        <td className={styles.tdAsset}>
                          <Link href={`/workflow?asset=${encodeURIComponent(row.asset)}`}>{row.asset}</Link>
                          {rowBaseline ? <div style={{ fontSize: 10, color: "var(--text-muted)", fontWeight: 500 }}>{rowBaseline.asset_class.replace("_", " ")}</div> : null}
                        </td>
                        <td style={{ color: rowBaseline && row.score >= rowBaseline.signal_score_floor ? "var(--state-success)" : "var(--state-warning)" }}>
                          {row.score.toFixed(1)}
                          {rowBaseline ? <span style={{ fontSize: 10, color: "var(--text-muted)" }}> / {rowBaseline.signal_score_floor}</span> : null}
                        </td>
                        <td style={{ color: rowBaseline && row.confidence >= rowBaseline.confidence_floor ? "var(--state-success)" : "var(--state-warning)" }}>
                          {(row.confidence * 100).toFixed(1)}%
                          {rowBaseline ? <span style={{ fontSize: 10, color: "var(--text-muted)" }}> / {(rowBaseline.confidence_floor * 100).toFixed(0)}%</span> : null}
                        </td>
                        <td className={row.decision.approved ? styles.tdApproved : styles.tdDenied}>
                          {row.decision.approved ? "YES" : "NO"}
                        </td>
                        <td style={{ fontVariantNumeric: "tabular-nums" }}>
                          ${row.decision.allowed_risk_amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </td>
                        <td style={{ textTransform: "capitalize" }}>{row.decision.selected_execution_mode.replace(/_/g, " ")}</td>
                        <td className={styles.tdMuted}>
                          {row.decision.blocked_reasons.length > 0 ? row.decision.blocked_reasons.join(", ") : "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

export default function RiskPage() {
  return (
    <Suspense fallback={null}>
      <RiskPageContent />
    </Suspense>
  );
}