"use client";

import Link from "next/link";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import {
  evaluateRisk,
  getAssets,
  getMarketDataBars,
  getMarketDataNews,
  getMarketDataStatus,
  getOpportunities,
  getPerformanceStats,
  getRegime,
  runSweep,
  type AssetResponse,
  type MarketDataBarItem,
  type MarketDataNewsItem,
  type MarketDataStatusItem,
  type RankedOpportunity,
} from "../../lib/api";
import { useLivePolling } from "../../lib/hooks/useLivePolling";
import type { RiskDecisionResponse, SignalDirection, SignalResponse, Timeframe } from "../../lib/types";
import styles from "../../styles/pages/signals.module.css";

const CHART_WIDTH = 980;
const CHART_HEIGHT = 320;
const CHART_PAD = 24;

const CHART_WINDOWS = ["1D", "1W", "1M", "3M", "6M", "All"] as const;
type ChartWindow = (typeof CHART_WINDOWS)[number];
const CHART_WINDOW_BARS: Record<ChartWindow, number | null> = { "1D": 1, "1W": 7, "1M": 30, "3M": 63, "6M": 126, "All": null };

const TIMEFRAMES: Timeframe[] = ["15m", "1h", "4h", "1d"];

function volumeOrZero(volume: number | null): number {
  return volume ?? 0;
}

function toSignalDirection(value: string): SignalDirection {
  if (value === "long" || value === "short" || value === "flat") return value;
  return "flat";
}

function toSignalFromOpportunity(opp: RankedOpportunity, timeframe: Timeframe): SignalResponse {
  return {
    asset: opp.asset,
    timeframe,
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
    thesis: `Live board risk pass from ${opp.setup_type}`,
    invalidators: ["opportunity_snapshot"],
    signal_score: opp.score,
    should_trade: true,
  };
}

function formatTs(value: string | null | undefined): string {
  if (!value) return "-";
  const t = Date.parse(value);
  if (!Number.isFinite(t)) return value;
  return new Date(t).toLocaleString();
}



interface BoardRow {
  asset: AssetResponse;
  status: MarketDataStatusItem | null;
  topOpportunity: RankedOpportunity | null;
}

function SignalsPageContent() {
  const searchParams = useSearchParams();
  const urlAsset = searchParams.get("asset")?.toUpperCase() ?? null;

  const [assets, setAssets] = useState<AssetResponse[]>([]);
  const [statusRows, setStatusRows] = useState<MarketDataStatusItem[]>([]);
  const [opportunities, setOpportunities] = useState<RankedOpportunity[]>([]);
  const [selectedAsset, setSelectedAsset] = useState<string>(urlAsset ?? "");
  const [selectedTimeframe, setSelectedTimeframe] = useState<Timeframe>("1d");
  const [news, setNews] = useState<MarketDataNewsItem[]>([]);
  const [bars, setBars] = useState<MarketDataBarItem[]>([]);
  // per-asset latest bars for the board table (symbol → last 2 bars)
  const [boardBars, setBoardBars] = useState<Record<string, MarketDataBarItem[]>>({});
  const [risk, setRisk] = useState<RiskDecisionResponse | null>(null);
  const [regime, setRegime] = useState<string>("unknown");
  const [overallWinRate, setOverallWinRate] = useState<number | null>(null);
  const [loadingBoard, setLoadingBoard] = useState<boolean>(true);
  const [loadingDetails, setLoadingDetails] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [sweepMessage, setSweepMessage] = useState<string | null>(null);
  const [sweepRunning, setSweepRunning] = useState<boolean>(false);
  const [lastSyncedAt, setLastSyncedAt] = useState<string>(new Date().toISOString());

  const boardRows = useMemo<BoardRow[]>(() => {
    const rows = assets.map((asset) => {
      const symbol = asset.symbol.toUpperCase();
      const status =
        statusRows.find((row) => row.asset_symbol.toUpperCase() === symbol && row.timeframe === selectedTimeframe) ??
        statusRows.find((row) => row.asset_symbol.toUpperCase() === symbol) ??
        null;
      const topOpportunity = opportunities.find((opp) => opp.asset.toUpperCase() === symbol) ?? null;
      return { asset, status, topOpportunity };
    });

    rows.sort((a, b) => {
      const scoreA = a.topOpportunity?.score ?? -1;
      const scoreB = b.topOpportunity?.score ?? -1;
      return scoreB - scoreA;
    });
    return rows;
  }, [assets, statusRows, opportunities, selectedTimeframe]);

  const selectedRow = useMemo(() => {
    const target = selectedAsset.toUpperCase();
    return boardRows.find((row) => row.asset.symbol.toUpperCase() === target) ?? null;
  }, [boardRows, selectedAsset]);

  const selectedAssetOpportunities = useMemo(() => {
    const target = selectedAsset.toUpperCase();
    return opportunities.filter((opp) => opp.asset.toUpperCase() === target).slice(0, 8);
  }, [opportunities, selectedAsset]);

  async function loadBoard() {
    setError(null);
    try {
      const [assetRes, oppRes, statusRes, regimeRes, perfRes] = await Promise.all([
        getAssets({ active_only: true }),
        getOpportunities(50),
        getMarketDataStatus(),
        getRegime(),
        getPerformanceStats(),
      ]);
      setAssets(assetRes.items);
      setOpportunities(oppRes.items);
      setStatusRows(statusRes.items);
      setRegime(regimeRes.regime);
      setOverallWinRate(perfRes.overall_win_rate);
      setLastSyncedAt(new Date().toISOString());

      if (!selectedAsset && assetRes.items.length > 0) {
        setSelectedAsset((urlAsset ?? assetRes.items[0].symbol).toUpperCase());
      }

      // Fetch last 2 daily bars for each asset to populate price/1d-change in the table
      const barsEntries = await Promise.all(
        assetRes.items.map(async (a) => {
          try {
            const r = await getMarketDataBars(a.symbol.toUpperCase(), "1d", 2);
            return [a.symbol.toUpperCase(), r.items] as [string, MarketDataBarItem[]];
          } catch {
            return [a.symbol.toUpperCase(), []] as [string, MarketDataBarItem[]];
          }
        })
      );
      setBoardBars(Object.fromEntries(barsEntries));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load live signal board.");
      setAssets([]);
      setOpportunities([]);
      setStatusRows([]);
    } finally {
      setLoadingBoard(false);
    }
  }

  async function loadSelectedAssetDetails(symbol: string) {
    if (!symbol) return;
    setLoadingDetails(true);
    try {
      const upper = symbol.toUpperCase();
      const [newsRes, barsRes] = await Promise.all([
        getMarketDataNews(upper, 8),
        getMarketDataBars(upper, selectedTimeframe, 140),
      ]);
      setNews(newsRes);
      setBars(barsRes.items);

      const topOpp = opportunities.find((opp) => opp.asset.toUpperCase() === upper) ?? null;
      if (!topOpp) {
        setRisk(null);
      } else {
        const riskRes = await evaluateRisk({
          signal: toSignalFromOpportunity(topOpp, selectedTimeframe),
          risk_context: {
            spread_bps: 10,
            daily_drawdown_pct: 1,
            consecutive_losses: 0,
            minutes_since_last_loss: null,
            correlated_exposure_count: 0,
            open_positions_count: 0,
            market_quality_flag: true,
            session_allowed: true,
            kill_switch_active: false,
            account_equity: 50000,
            requested_execution_mode: "paper",
          },
        });
        setRisk(riskRes);
      }
    } catch {
      setNews([]);
      setBars([]);
      setRisk(null);
    } finally {
      setLoadingDetails(false);
    }
  }

  async function handleRunSweep() {
    if (sweepRunning) return;
    setSweepRunning(true);
    setSweepMessage(null);
    try {
      const result = await runSweep();
      setSweepMessage(result.status === "ok" ? `Sweep complete: ${result.message}` : `Sweep failed: ${result.message}`);
      await loadBoard();
    } catch (sweepError) {
      setSweepMessage(sweepError instanceof Error ? sweepError.message : "Sweep request failed.");
    } finally {
      setSweepRunning(false);
    }
  }

  useEffect(() => {
    void loadBoard();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useLivePolling(() => loadBoard(), 15000, { enabled: true, runImmediately: false });

  useEffect(() => {
    if (!selectedAsset) return;
    void loadSelectedAssetDetails(selectedAsset);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedAsset, selectedTimeframe, opportunities]);

  useLivePolling(() => {
    if (!selectedAsset) return Promise.resolve();
    return loadSelectedAssetDetails(selectedAsset);
  }, 20000, { enabled: !!selectedAsset, runImmediately: false });

  const [hoverIdx, setHoverIdx] = useState<number | null>(null);
  const [chartWindow, setChartWindow] = useState<ChartWindow>("All");

  const chartBars = useMemo(() => {
    const n = CHART_WINDOW_BARS[chartWindow];
    return n === null ? bars : bars.slice(-n);
  }, [bars, chartWindow]);

  const chartGeo = useMemo(() => {
    if (chartBars.length < 1) return null;
    const PRICE_TOP = CHART_PAD;
    const PRICE_BOT = 235;
    const VOL_TOP = 248;
    const VOL_BOT = 296;
    const n = chartBars.length;
    const xRange = CHART_WIDTH - CHART_PAD * 2;
    const priceMin = Math.min(...chartBars.map((b) => b.low)) * 0.9995;
    const priceMax = Math.max(...chartBars.map((b) => b.high)) * 1.0005;
    const priceSpread = Math.max(1e-9, priceMax - priceMin);
    const volMax = Math.max(...chartBars.map((b) => volumeOrZero(b.volume)), 1) * 1.05;
    const xOf = (i: number) => n === 1 ? CHART_WIDTH / 2 : CHART_PAD + (i / Math.max(1, n - 1)) * xRange;
    const yPrice = (p: number) => PRICE_TOP + (1 - (p - priceMin) / priceSpread) * (PRICE_BOT - PRICE_TOP);
    const yVol = (v: number) => VOL_BOT - (v / volMax) * (VOL_BOT - VOL_TOP);
    const closePts = n === 1
      ? `${CHART_PAD.toFixed(1)},${yPrice(chartBars[0].close).toFixed(1)} ${(CHART_WIDTH - CHART_PAD).toFixed(1)},${yPrice(chartBars[0].close).toFixed(1)}`
      : chartBars.map((b, i) => `${xOf(i).toFixed(1)},${yPrice(b.close).toFixed(1)}`).join(" ");
    const areaPolygon = n === 1
      ? `${CHART_PAD.toFixed(1)},${PRICE_BOT} ${CHART_PAD.toFixed(1)},${yPrice(chartBars[0].close).toFixed(1)} ${(CHART_WIDTH - CHART_PAD).toFixed(1)},${yPrice(chartBars[0].close).toFixed(1)} ${(CHART_WIDTH - CHART_PAD).toFixed(1)},${PRICE_BOT}`
      : `${xOf(0).toFixed(1)},${PRICE_BOT} ${closePts} ${xOf(n - 1).toFixed(1)},${PRICE_BOT}`;
    const sma20Pts: string[] = [];
    for (let i = 19; i < n; i++) {
      const avg = chartBars.slice(i - 19, i + 1).reduce((s, b) => s + b.close, 0) / 20;
      sma20Pts.push(`${xOf(i).toFixed(1)},${yPrice(avg).toFixed(1)}`);
    }
    const barW = n === 1 ? xRange * 0.4 : Math.max(1, (xRange / n) * 0.7);
    const volBars = chartBars.map((b, i) => ({
      x: (n === 1 ? (CHART_WIDTH - xRange * 0.4) / 2 : xOf(i) - barW / 2),
      y: yVol(volumeOrZero(b.volume)),
      w: barW,
      h: Math.max(1, VOL_BOT - yVol(volumeOrZero(b.volume))),
      up: b.close >= b.open,
    }));
    return { closePts, areaPolygon, sma20Pts: sma20Pts.join(" "), volBars, xOf, yPrice, PRICE_BOT, VOL_BOT };
  }, [chartBars]);

  const handleChartMouseMove = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (!chartGeo || chartBars.length < 1) return;
      if (chartBars.length === 1) { setHoverIdx(0); return; }
      const rect = e.currentTarget.getBoundingClientRect();
      const svgX = ((e.clientX - rect.left) / rect.width) * CHART_WIDTH;
      const xRange = CHART_WIDTH - CHART_PAD * 2;
      const ratio = Math.max(0, Math.min(1, (svgX - CHART_PAD) / xRange));
      setHoverIdx(Math.round(ratio * (chartBars.length - 1)));
    },
    [chartGeo, chartBars.length],
  );

  const handleChartMouseLeave = useCallback(() => setHoverIdx(null), []);

  const latestClose = bars.length > 0 ? bars[bars.length - 1].close : null;
  const closeDelta =
    bars.length > 1 ? ((bars[bars.length - 1].close - bars[0].close) / Math.max(bars[0].close, 1e-9)) * 100 : null;

  // Derived indicators for KPI grid — computed from the selected asset's bars
  const sma20 = useMemo(() => {
    if (bars.length < 20) return null;
    const last20 = bars.slice(-20).map((b) => b.close);
    return last20.reduce((a, b) => a + b, 0) / 20;
  }, [bars]);

  const volRatio = useMemo(() => {
    if (bars.length < 2) return null;
    const last = bars[bars.length - 1];
    const avg20 = bars.slice(-21, -1).map((b) => volumeOrZero(b.volume));
    if (avg20.length === 0) return null;
    const avg = avg20.reduce((a, b) => a + b, 0) / avg20.length;
    return avg > 0 ? volumeOrZero(last.volume) / avg : null;
  }, [bars]);

  const dayOHLC = bars.length > 0 ? bars[bars.length - 1] : null;

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <div className={styles.statusBanner}>
          Live feed synced: {formatTs(lastSyncedAt)} | Regime: {regime.toUpperCase()} | Win rate: {overallWinRate !== null ? `${(overallWinRate * 100).toFixed(1)}%` : "-"}
        </div>

        <section className={styles.panel}>
          <div className={styles.panelHeader}>
            <h3 className={styles.panelTitle}>Live Signal Feed</h3>
            <div className={styles.dashboardControls}>
              <span className={styles.assetLabel}>{boardRows.length} assets tracked</span>
              <button type="button" onClick={() => void handleRunSweep()} className={styles.sweepButton} disabled={sweepRunning}>
                {sweepRunning ? "Running sweep..." : "Run Sweep"}
              </button>
            </div>
          </div>

          {error ? <p className={styles.errorBox}>{error}</p> : null}
          {sweepMessage ? <p className={styles.assetLabel}>{sweepMessage}</p> : null}
          {loadingBoard ? <p className={styles.emptyMsg}>Loading live feed...</p> : null}

          {!loadingBoard && boardRows.length === 0 ? (
            <p className={styles.emptyMsg}>No active assets available.</p>
          ) : (
            <div className={styles.tableWrap}>
              <table className={styles.feedTable}>
                <thead>
                  <tr>
                    <th>Asset</th>
                    <th>Class</th>
                    <th>Price</th>
                    <th>1d %</th>
                    <th>Direction</th>
                    <th>Score</th>
                    <th>Confidence</th>
                    <th>Entry Range</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {boardRows.map((row) => {
                    const active = selectedAsset.toUpperCase() === row.asset.symbol.toUpperCase();
                    const sym = row.asset.symbol.toUpperCase();
                    const assetBars = boardBars[sym] ?? [];
                    const lastClose = assetBars.length > 0 ? assetBars[assetBars.length - 1].close : null;
                    const prevClose = assetBars.length > 1 ? assetBars[assetBars.length - 2].close : null;
                    const change1d = lastClose !== null && prevClose !== null && prevClose > 0
                      ? ((lastClose - prevClose) / prevClose) * 100
                      : null;
                    return (
                      <tr key={row.asset.id} className={active ? styles.activeRow : undefined}>
                        <td>
                          <button
                            type="button"
                            className={styles.assetButton}
                            onClick={() => setSelectedAsset(row.asset.symbol.toUpperCase())}
                          >
                            {row.asset.symbol}
                          </button>
                        </td>
                        <td>{row.asset.asset_class}</td>
                        <td>{lastClose !== null ? lastClose.toFixed(lastClose < 10 ? 5 : 2) : "-"}</td>
                        <td style={{ color: change1d === null ? undefined : change1d >= 0 ? "var(--state-success)" : "var(--state-error)" }}>
                          {change1d !== null ? `${change1d >= 0 ? "+" : ""}${change1d.toFixed(2)}%` : "-"}
                        </td>
                        <td>{row.topOpportunity?.direction ?? "-"}</td>
                        <td>{row.topOpportunity ? row.topOpportunity.score.toFixed(1) : "-"}</td>
                        <td>{row.topOpportunity ? `${(row.topOpportunity.confidence * 100).toFixed(1)}%` : "-"}</td>
                        <td>
                          {row.topOpportunity
                            ? `${row.topOpportunity.entry_low.toFixed(4)} - ${row.topOpportunity.entry_high.toFixed(4)}`
                            : "-"}
                        </td>
                        <td>
                          <div className={styles.actionLinks}>
                            <Link href={`/workflow?asset=${encodeURIComponent(row.asset.symbol)}`}>Workflow</Link>
                            <Link href={`/risk?asset=${encodeURIComponent(row.asset.symbol)}`}>Risk</Link>
                            <Link href={`/execution?asset=${encodeURIComponent(row.asset.symbol)}`}>Execution</Link>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {selectedRow ? (
          <section className={styles.panel}>
            <div className={styles.panelHeader}>
              <h3 className={styles.panelTitle}>{selectedRow.asset.symbol} Live Asset Dashboard</h3>
              <div className={styles.dashboardControls}>
                <span className={styles.assetLabel}>{selectedRow.asset.name ?? "Unnamed asset"}</span>
                <select
                  className={styles.timeframeSelect}
                  value={selectedTimeframe}
                  onChange={(event) => setSelectedTimeframe(event.target.value as Timeframe)}
                >
                  {TIMEFRAMES.map((tf) => (
                    <option key={tf} value={tf}>
                      {tf}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className={styles.kpiGrid}>
              <div className={styles.kpiCard}>
                <span className={styles.kpiLabel}>Last Close</span>
                <strong className={styles.kpiValue}>{latestClose !== null ? latestClose.toFixed(5) : "-"}</strong>
              </div>
              <div className={styles.kpiCard}>
                <span className={styles.kpiLabel}>Period Change</span>
                <strong className={styles.kpiValue}>{closeDelta !== null ? `${closeDelta.toFixed(2)}%` : "-"}</strong>
              </div>
              <div className={styles.kpiCard}>
                <span className={styles.kpiLabel}>Top Signal Score</span>
                <strong className={styles.kpiValue}>{selectedRow.topOpportunity ? selectedRow.topOpportunity.score.toFixed(1) : "-"}</strong>
              </div>
              <div className={styles.kpiCard}>
                <span className={styles.kpiLabel}>Top Confidence</span>
                <strong className={styles.kpiValue}>
                  {selectedRow.topOpportunity ? `${(selectedRow.topOpportunity.confidence * 100).toFixed(1)}%` : "-"}
                </strong>
              </div>
              <div className={styles.kpiCard}>
                <span className={styles.kpiLabel}>Day High / Low</span>
                <strong className={styles.kpiValue}>
                  {dayOHLC ? `${dayOHLC.high.toFixed(dayOHLC.high < 10 ? 5 : 2)} / ${dayOHLC.low.toFixed(dayOHLC.low < 10 ? 5 : 2)}` : "-"}
                </strong>
              </div>
              <div className={styles.kpiCard}>
                <span className={styles.kpiLabel}>SMA20</span>
                <strong className={styles.kpiValue} style={{ color: sma20 === null || latestClose === null ? undefined : latestClose >= sma20 ? "var(--state-success)" : "var(--state-error)" }}>
                  {sma20 !== null ? sma20.toFixed(sma20 < 10 ? 5 : 2) : "-"}
                </strong>
              </div>
              <div className={styles.kpiCard}>
                <span className={styles.kpiLabel}>Vol vs 20d Avg</span>
                <strong className={styles.kpiValue} style={{ color: volRatio === null ? undefined : volRatio >= 1.5 ? "var(--state-warning)" : undefined }}>
                  {volRatio !== null ? `${volRatio.toFixed(2)}×` : "-"}
                </strong>
              </div>
              <div className={styles.kpiCard}>
                <span className={styles.kpiLabel}>Risk Decision</span>
                <strong className={styles.kpiValue}>{risk ? (risk.approved ? "Approved" : "Blocked") : "-"}</strong>
              </div>
            </div>

            <div className={styles.chartCard}>
              <div className={styles.panelHeader}>
                <h4 className={styles.subTitle}>Historic Price ({selectedTimeframe})</h4>
                <div className={styles.chartWindowBar}>
                  {CHART_WINDOWS.map((w) => (
                    <button
                      key={w}
                      type="button"
                      className={`${styles.chartWindowBtn}${chartWindow === w ? ` ${styles.chartWindowBtnActive}` : ""}`}
                      onClick={() => { setChartWindow(w); setHoverIdx(null); }}
                    >
                      {w}
                    </button>
                  ))}
                  <span className={styles.assetLabel}>{chartBars.length} bars</span>
                </div>
              </div>
              {chartBars.length < 1 ? (
                <p className={styles.emptyMsg}>No historical bars available for this asset/timeframe yet.</p>
              ) : (
                <svg
                  viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
                  className={styles.chartSvg}
                  role="img"
                  aria-label="Historical price chart"
                  onMouseMove={handleChartMouseMove}
                  onMouseLeave={handleChartMouseLeave}
                >
                  <defs>
                    <linearGradient id="priceAreaGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--state-info)" stopOpacity="0.22" />
                      <stop offset="100%" stopColor="var(--state-info)" stopOpacity="0.02" />
                    </linearGradient>
                  </defs>
                  <rect x="0" y="0" width={CHART_WIDTH} height={CHART_HEIGHT} rx="12" fill="var(--surface-soft)" />
                  {chartGeo && (
                    <>
                      <line x1={CHART_PAD} y1={chartGeo.PRICE_BOT + 6} x2={CHART_WIDTH - CHART_PAD} y2={chartGeo.PRICE_BOT + 6} stroke="var(--surface-border)" strokeWidth="1" />
                      <polygon points={chartGeo.areaPolygon} fill="url(#priceAreaGrad)" />
                      {chartGeo.volBars.map((b, i) => (
                        <rect key={i} x={b.x} y={b.y} width={b.w} height={b.h} fill={b.up ? "var(--state-success)" : "var(--state-error)"} opacity="0.5" />
                      ))}
                      {chartGeo.sma20Pts && (
                        <polyline points={chartGeo.sma20Pts} fill="none" stroke="var(--state-warning)" strokeWidth="1.5" strokeDasharray="5 3" strokeLinecap="round" />
                      )}
                      <polyline points={chartGeo.closePts} fill="none" stroke="var(--state-info)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                      {hoverIdx !== null && chartBars[hoverIdx] && (() => {
                        const bar = chartBars[hoverIdx];
                        const x = chartGeo.xOf(hoverIdx);
                        const y = chartGeo.yPrice(bar.close);
                        const tipLeft = hoverIdx > chartBars.length * 0.6;
                        const tipX = tipLeft ? x - 148 : x + 12;
                        const tipY = CHART_PAD + 4;
                        const precision = bar.close < 10 ? 5 : 2;
                        const vol = volumeOrZero(bar.volume);
                        const volStr = vol >= 1_000_000 ? `${(vol / 1_000_000).toFixed(1)}M` : vol >= 1_000 ? `${(vol / 1_000).toFixed(0)}K` : `${vol}`;
                        const date = bar.ts ? new Date(bar.ts).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "";
                        return (
                          <g>
                            <line x1={x} y1={CHART_PAD} x2={x} y2={chartGeo.VOL_BOT} stroke="var(--text-muted)" strokeWidth="1" strokeDasharray="4 3" opacity="0.7" />
                            <circle cx={x} cy={y} r="4" fill="var(--state-info)" stroke="var(--surface-fill)" strokeWidth="2" />
                            <rect x={tipX} y={tipY} width={136} height={112} rx="8" fill="var(--surface-fill)" stroke="var(--surface-border)" strokeWidth="1" />
                            <text x={tipX + 10} y={tipY + 18} fill="var(--text-strong)" fontSize="11" fontWeight="700">{date}</text>
                            <text x={tipX + 10} y={tipY + 36} fill="var(--text-muted)" fontSize="10">O <tspan fill="var(--text-primary)">{bar.open.toFixed(precision)}</tspan></text>
                            <text x={tipX + 10} y={tipY + 52} fill="var(--text-muted)" fontSize="10">H <tspan fill="var(--state-success)">{bar.high.toFixed(precision)}</tspan></text>
                            <text x={tipX + 10} y={tipY + 68} fill="var(--text-muted)" fontSize="10">L <tspan fill="var(--state-error)">{bar.low.toFixed(precision)}</tspan></text>
                            <text x={tipX + 10} y={tipY + 84} fill="var(--text-muted)" fontSize="10">C <tspan fill="var(--state-info)">{bar.close.toFixed(precision)}</tspan></text>
                            <text x={tipX + 10} y={tipY + 100} fill="var(--text-muted)" fontSize="10">Vol <tspan fill="var(--text-primary)">{volStr}</tspan></text>
                          </g>
                        );
                      })()}
                    </>
                  )}
                </svg>
              )}
            </div>

            <div className={styles.detailGrid}>
              <div className={styles.detailCard}>
                <h4 className={styles.subTitle}>Risk Snapshot</h4>
                {loadingDetails ? (
                  <p className={styles.emptyMsg}>Evaluating risk...</p>
                ) : !risk ? (
                  <p className={styles.emptyMsg}>No risk decision available for this asset.</p>
                ) : (
                  <div className={styles.riskGrid}>
                    <div>
                      <span className={styles.kpiLabel}>Status</span>
                      <strong className={styles.kpiValue}>{risk.approved ? "Approved" : "Blocked"}</strong>
                    </div>
                    <div>
                      <span className={styles.kpiLabel}>Allowed Risk</span>
                      <strong className={styles.kpiValue}>{risk.allowed_risk_amount.toFixed(2)}</strong>
                    </div>
                    <div>
                      <span className={styles.kpiLabel}>Execution Mode</span>
                      <strong className={styles.kpiValue}>{risk.selected_execution_mode}</strong>
                    </div>
                    <div>
                      <span className={styles.kpiLabel}>Reasons</span>
                      <strong className={styles.kpiValue}>{risk.blocked_reasons.length > 0 ? risk.blocked_reasons.join(", ") : "none"}</strong>
                    </div>
                  </div>
                )}
              </div>

              <div className={styles.detailCard}>
                <h4 className={styles.subTitle}>Latest Opportunities</h4>
                {selectedAssetOpportunities.length === 0 ? (
                  <p className={styles.emptyMsg}>No opportunities for this asset yet.</p>
                ) : (
                  <div className={styles.tableWrap}>
                    <table className={styles.assetMiniTable}>
                      <thead>
                        <tr>
                          <th>Direction</th>
                          <th>Score</th>
                          <th>Confidence</th>
                          <th>Entry</th>
                          <th>Stop</th>
                          <th>Target</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedAssetOpportunities.map((opp) => (
                          <tr key={opp.signal_id}>
                            <td>{opp.direction}</td>
                            <td>{opp.score.toFixed(1)}</td>
                            <td>{(opp.confidence * 100).toFixed(1)}%</td>
                            <td>{opp.entry_low.toFixed(4)} - {opp.entry_high.toFixed(4)}</td>
                            <td>{opp.stop_price.toFixed(4)}</td>
                            <td>{opp.target_price.toFixed(4)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>

            <div className={styles.detailCard}>
              <h4 className={styles.subTitle}>Recent News</h4>
              {news.length === 0 ? (
                <p className={styles.emptyMsg}>No recent news available for this asset.</p>
              ) : (
                <div className={styles.newsGrid}>
                  {news.map((item) => (
                    <div key={item.id} className={styles.newsItem}>
                      <strong className={styles.newsHeadline}>{item.headline}</strong>
                      <span className={styles.newsMeta}>
                        {(item.source_name ?? "Unknown source") + " • " + formatTs(item.published_at)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>
        ) : null}
      </div>
    </main>
  );
}

export default function SignalsPage() {
  return (
    <Suspense fallback={null}>
      <SignalsPageContent />
    </Suspense>
  );
}
