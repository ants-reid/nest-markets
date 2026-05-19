"use client";

import { Suspense } from "react";
import type React from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { OperatorNotificationSurface } from "../../components/OperatorNotificationSurface";
import { ExecutionJournalPanel } from "../../components/ExecutionJournalPanel";
import { ChartPanel, PriceLevelChart } from "../../components/chart";
import { LearnTooltip } from "../../components/LearnTooltip";
import styles from "../../styles/pages/execution.module.css";
import { useExecutionPageController } from "../../lib/hooks/useExecutionPageController";
import {
  type PaperExecutionHistoryResponse,
} from "../../lib/api";
import type { PaperExecutionResponse } from "../../lib/types";

const PAGE_SIZE = 10;

const STATUS_OPTIONS = ["", "accepted", "filled", "closed", "rejected", "canceled", "new"];

const STATUS_DOT: Record<string, string> = {
  filled: "var(--state-success)",
  accepted: "var(--state-info)",
  closed: "var(--accent-primary)",
  submitted: "var(--accent-secondary)",
  new: "var(--text-muted)",
  rejected: "var(--state-danger)",
  canceled: "var(--state-warning)",
  expired: "var(--text-muted)",
};

function statusDot(status: string): string {
  return STATUS_DOT[status.toLowerCase()] ?? "var(--text-muted)";
}

function statusColor(status: string): string {
  const map: Record<string, string> = {
    filled: "var(--state-success)",
    accepted: "var(--state-info)",
    closed: "var(--accent-primary)",
    submitted: "var(--accent-secondary)",
    new: "var(--text-muted)",
    rejected: "var(--state-danger)",
    canceled: "var(--state-warning)",
    expired: "var(--text-muted)",
  };
  return map[status.toLowerCase()] ?? "var(--text-strong)";
}

interface TradeIntelligence {
  rrRatio: number | null;
  riskPerUnit: number;
  rewardPerUnit: number;
  riskNotional: number;
  rewardNotional: number;
  stopDistancePct: number;
  targetDistancePct: number;
  outcomeLabel: string;
  outcomeColor: string;
}

function deriveTradeIntelligence(detail: PaperExecutionResponse): TradeIntelligence {
  const isBuy = detail.side.toLowerCase() === "buy";
  const fill = detail.fill_price;
  const stop = detail.stop_price;
  const target = detail.target_price;
  const qty = detail.qty;

  const riskPerUnit = Math.abs(fill - stop);
  const rewardPerUnit = Math.abs(target - fill);
  const rrRatio = riskPerUnit > 0 ? rewardPerUnit / riskPerUnit : null;
  const riskNotional = riskPerUnit * qty;
  const rewardNotional = rewardPerUnit * qty;

  const stopDistancePct = fill > 0 ? (riskPerUnit / fill) * 100 : 0;
  const targetDistancePct = fill > 0 ? (rewardPerUnit / fill) * 100 : 0;

  const statusLow = detail.status.toLowerCase();
  const outcomeMap: Record<string, { label: string; color: string }> = {
    filled:    { label: "Active — position is live", color: "var(--state-success)" },
    accepted:  { label: "Pending fill", color: "var(--state-info)" },
    submitted: { label: "Pending acceptance", color: "var(--accent-secondary)" },
    new:       { label: "Queued, not yet submitted", color: "var(--text-muted)" },
    closed:    { label: "Closed — no exit price in payload; notional proxy only", color: "var(--accent-primary)" },
    rejected:  { label: "Rejected before fill", color: "var(--state-danger)" },
    canceled:  { label: "Canceled before fill", color: "var(--state-warning)" },
    expired:   { label: "Expired before fill", color: "var(--text-muted)" },
  };
  const outcome = outcomeMap[statusLow] ?? { label: "Unknown status", color: "var(--text-muted)" };

  void isBuy; // acknowledged; direction is encoded in side label and stop/target positions

  return {
    rrRatio,
    riskPerUnit,
    rewardPerUnit,
    riskNotional,
    rewardNotional,
    stopDistancePct,
    targetDistancePct,
    outcomeLabel: outcome.label,
    outcomeColor: outcome.color,
  };
}

function IntelligenceRow({ label, value, mono = false }: { label: React.ReactNode; value: string; mono?: boolean }) {
  return (
    <div data-rs="intelligence-row" className={styles.intelligenceRow}>
      <span className={styles.intelligenceLabel}>{label}</span>
      <span className={mono ? styles.intelligenceValueMono : styles.intelligenceValue}>{value}</span>
    </div>
  );
}

function ExecutionPageContent() {
  const searchParams = useSearchParams();
  const urlAsset = searchParams.get("asset");

  const {
    statusFilter,
    offset,
    list,
    isListLoading,
    listError,
    canGoPrev,
    canGoNext,
    titleStatus,
    selectedExecutionId,
    detail,
    isDetailLoading,
    detailError,
    history,
    isHistoryLoading,
    historyError,
    positions,
    isPositionsLoading,
    positionsError,
    onFilterChange,
    onSelectExecution,
    onPrevPage,
    onNextPage,
    onReloadList,
  } = useExecutionPageController();

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <OperatorNotificationSurface title="Operator Notifications" maxItems={3} />

        <section className={styles.panel}>
          <div className={styles.sectionHeader}>
            <div>
              <h2 className={styles.sectionTitle}>Execution List</h2>
              <p className={styles.sectionSubtitle}>Showing {titleStatus} from /execution/paper</p>
              {urlAsset ? <p className={styles.sectionSubtitleSm}>Context asset: {urlAsset}</p> : null}
            </div>

            <div className={styles.filterRow}>
              <label className={styles.filterLabel}>Status</label>
              <select
                value={statusFilter}
                onChange={(event) => onFilterChange(event.target.value)}
                className={styles.filterSelect}
              >
                {STATUS_OPTIONS.map((value) => (
                  <option key={value || "all"} value={value}>
                    {value || "all"}
                  </option>
                ))}
              </select>
              <button type="button" onClick={onReloadList} className={styles.filterButton}>
                Refresh
              </button>
            </div>
          </div>

          <div className={styles.listArea}>
            {isListLoading ? <div className={styles.loadingMsg}>Loading executions...</div> : null}
            {listError ? <div className={styles.errorBox}>{listError}</div> : null}
            {!isListLoading && !listError && list.length === 0 ? (
              <div className={styles.emptyMsg}>No executions found for this filter.</div>
            ) : null}

            {!isListLoading && !listError && list.length > 0 ? (
              <div className={styles.listGrid}>
                {list.map((item) => {
                  const isSelected = item.execution_id === selectedExecutionId;
                  return (
                    <button
                      key={item.execution_id}
                      type="button"
                      onClick={() => onSelectExecution(item.execution_id)}
                      className={`${styles.executionItem} ${isSelected ? styles.executionItemSelected : ""}`}
                    >
                      <div className={styles.executionItemTop}>
                        <span className={styles.executionIdBadge}>{item.execution_id.slice(0, 8)}…</span>
                        <span className={styles.executionAssetBadge}>{item.asset}</span>
                        <span className={styles.executionTimeframe}>{item.timeframe}</span>
                      </div>
                      <div className={styles.executionItemBottom}>
                        <span className={styles.statusDot} style={{ background: statusDot(item.status) }} />
                        <span className={styles.statusText} style={{ color: statusColor(item.status) }}>{item.status}</span>
                        <span className={styles.statusSide}>{item.side}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            ) : null}
          </div>

          <div className={styles.pagination}>
            <button type="button" disabled={!canGoPrev} onClick={onPrevPage} className={styles.paginationBtn}>← Prev</button>
            <button type="button" disabled={!canGoNext} onClick={onNextPage} className={styles.paginationBtn}>Next →</button>
            <span className={styles.pageInfo}>page {Math.floor(offset / PAGE_SIZE) + 1} &middot; offset {offset}</span>
          </div>
        </section>

        <section className={styles.panel}>
          <div className={styles.sectionHeader}>
            <div>
              <h2 className={styles.sectionTitle} style={{ fontSize: 22 }}>Open Positions</h2>
              <p className={styles.sectionSubtitle}>Current persisted positions from /execution/positions</p>
            </div>
          </div>

          <div className={styles.listArea}>
            {isPositionsLoading ? <div className={styles.loadingMsg}>Loading positions...</div> : null}
            {positionsError ? <div className={styles.errorBox}>{positionsError}</div> : null}
            {!isPositionsLoading && !positionsError && positions.length === 0 ? (
              <div className={styles.emptyMsg}>No open positions.</div>
            ) : null}
            {!isPositionsLoading && !positionsError && positions.length > 0 ? (
              <div className={styles.listGrid}>
                {positions.map((position) => (
                  <div key={position.id} className={styles.positionItem}>
                    <div>
                      <div className={styles.fieldLabel}>Asset</div>
                      <div className={styles.fieldValue}>{position.asset_symbol}</div>
                    </div>
                    <div>
                      <div className={styles.fieldLabel}>Side</div>
                      <div className={styles.fieldValue}>{position.side}</div>
                    </div>
                    <div>
                      <div className={styles.fieldLabel}>Qty</div>
                      <div className={styles.fieldValueMono}>{position.qty ?? "-"}</div>
                    </div>
                    <div>
                      <div className={styles.fieldLabel}>Entry</div>
                      <div className={styles.fieldValueMono}>{position.avg_entry_price?.toFixed(4) ?? "-"}</div>
                    </div>
                    <div>
                      <div className={styles.fieldLabel}>Unrealized PnL</div>
                      <div className={styles.fieldValueMono} style={{ color: (position.unrealized_pnl ?? 0) >= 0 ? "var(--state-success)" : "var(--state-danger)" }}>
                        {position.unrealized_pnl?.toFixed(2) ?? "0.00"}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        </section>

        <section data-rs="two-col" className={styles.twoCol}>
          <div className={styles.panel}>
            <h3 className={styles.panelTitle}>Current State</h3>
            {!selectedExecutionId ? (
              <p className={styles.loadingMsg} style={{ marginTop: 10 }}>Select an execution to see detail.</p>
            ) : null}
            {isDetailLoading ? <p className={styles.loadingMsg}>Loading execution detail...</p> : null}
            {detailError ? <div className={styles.errorBox}>{detailError}</div> : null}
            {!isDetailLoading && !detailError && detail ? (
              <div className={styles.detailGrid}>
                {[
                  { label: "ID", value: detail.execution_id, mono: true },
                  { label: "Status", value: detail.status, mono: false },
                  { label: "Asset", value: detail.asset, mono: false },
                  { label: "Timeframe", value: detail.timeframe, mono: false },
                  { label: "Side", value: detail.side, mono: false },
                  { label: "Qty", value: String(detail.qty), mono: true },
                  { label: "Notional", value: `$${detail.notional.toFixed(2)}`, mono: true },
                  { label: "Fill Price", value: detail.fill_price.toFixed(4), mono: true },
                  { label: "Stop", value: detail.stop_price.toFixed(4), mono: true },
                  { label: "Target", value: detail.target_price.toFixed(4), mono: true },
                ].map(({ label, value, mono }) => (
                  <div data-rs="detail-grid" key={label} className={styles.detailRow}>
                    <span className={styles.detailLabel}>{label}</span>
                    <span
                      className={mono ? styles.detailValueMono : styles.detailValue}
                      style={label === "Status" ? { color: statusColor(value), fontWeight: 700, wordBreak: "break-all" } : { wordBreak: "break-all" }}
                    >
                      {label === "Status" ? (
                        <span className={styles.statusInline}>
                          <span className={styles.statusDotSm} style={{ background: statusDot(value) }} />
                          {value}
                        </span>
                      ) : value}
                    </span>
                  </div>
                ))}
                <div className={styles.workflowLink}>
                  <Link href={`/workflow?asset=${encodeURIComponent(detail.asset)}&executionId=${encodeURIComponent(detail.execution_id)}&status=${encodeURIComponent(detail.status)}`}>
                    Open workflow with this context →
                  </Link>
                </div>
              </div>
            ) : null}
          </div>

          <div className={styles.panel}>
            <h3 className={styles.panelTitle}>Lifecycle History</h3>
            {!selectedExecutionId ? <p className={styles.loadingMsg}>Select an execution to see history.</p> : null}
            {isHistoryLoading ? <p className={styles.loadingMsg}>Loading execution history...</p> : null}
            {historyError ? <div className={styles.errorBox}>{historyError}</div> : null}
            {!isHistoryLoading && !historyError && history ? (
              <div className={styles.timelineGrid}>
                {history.events.map((event, idx) => (
                  <div data-rs="detail-grid" key={event} className={styles.timelineItem}>
                    <div className={styles.timelineIndicator}>
                      <div
                        className={styles.timelineDot}
                        style={{
                          background: idx === 0 ? "var(--text-strong)" : "var(--surface-border)",
                          border: `2px solid ${idx === 0 ? "var(--state-success)" : "var(--surface-border)"}`,
                        }}
                      />
                      {idx < history.events.length - 1 ? <div className={styles.timelineLine} /> : null}
                    </div>
                    <span
                      className={styles.detailValue}
                      style={{ color: idx === 0 ? "var(--text-body)" : "var(--text-muted)", fontWeight: idx === 0 ? 600 : 400, paddingTop: 2 }}
                    >
                      {event}
                    </span>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        </section>

        <section data-rs="two-col" className={styles.twoCol}>
          {/* Trade Intelligence panel */}
          <div className={styles.panel}>
            <h3 className={styles.panelTitle}>Trade Intelligence</h3>
            <p className={styles.panelSubtitle}>
              Derived from fill, stop, target, and qty. No close price in payload — closed positions show notional proxy only.
            </p>

            {!selectedExecutionId ? (
              <p className={styles.loadingMsg}>Select an execution to see trade intelligence.</p>
            ) : null}

            {isDetailLoading ? <p className={styles.loadingMsg}>Loading...</p> : null}

            {detailError ? (
              <div className={styles.errorBox}>Detail failed to load. Intelligence unavailable.</div>
            ) : null}

            {!isDetailLoading && !detailError && detail ? (() => {
              const intel = deriveTradeIntelligence(detail);
              return (
                <div style={{ display: "grid", gap: 16 }}>
                  <div className={styles.outcomeLabel} style={{ color: intel.outcomeColor }}>
                    {intel.outcomeLabel}
                  </div>

                  <ChartPanel
                    title={
                      <LearnTooltip
                        explain={{
                          beginner: "Price Levels show where you entered, where you exit for a loss (stop), and where you exit for profit (target).",
                          intermediate: "Trade map of fill/stop/target levels with reward and risk zones.",
                          experienced: "Execution level map with stop/target geometry around fill.",
                          expert: "Visual level structure: fill, stop, target with risk-reward zoned context.",
                        }}
                      >
                        Price Levels
                      </LearnTooltip>
                    }
                    subtitle={`${detail.asset} · ${detail.side.toUpperCase()} · ${detail.status}`}
                  >
                    <PriceLevelChart
                      fill={detail.fill_price}
                      stop={detail.stop_price}
                      target={detail.target_price}
                      side={detail.side}
                      status={detail.status}
                      asset={detail.asset}
                      qty={detail.qty}
                    />
                  </ChartPanel>

                  <div className={styles.intelligenceGrid}>
                    <IntelligenceRow
                      label={<LearnTooltip explain={{ beginner: "Risk-to-Reward ratio: how much you could gain vs. how much you risk. A 2:1 R:R means you could gain twice what you risk.", intermediate: "R:R = reward per unit / risk per unit. Aim for ≥2:1 for a positive edge.", experienced: "R:R ratio. Minimum viable: 1:1. Institutionally preferred: 2:1+.", expert: "R = target_distance / stop_distance at fill. Basis for position sizing via Kelly/fixed-fraction." }}>R:R Ratio</LearnTooltip>}
                      value={intel.rrRatio !== null ? `${intel.rrRatio.toFixed(2)} : 1` : "N/A — zero risk distance"}
                      mono
                    />
                    <IntelligenceRow
                      label={<LearnTooltip explain={{ beginner: "How much money you lose per unit if the stop is hit.", intermediate: "Risk per unit = |fill - stop|. Multiply by qty for notional risk.", experienced: "Per-unit stop distance in price terms.", expert: "|fill − stop|" }}>Risk / Unit</LearnTooltip>}
                      value={intel.riskPerUnit.toFixed(5)}
                      mono
                    />
                    <IntelligenceRow
                      label={<LearnTooltip explain={{ beginner: "How much money you gain per unit if the target is hit.", intermediate: "Reward per unit = |target - fill|.", experienced: "Per-unit target distance in price terms.", expert: "|target − fill|" }}>Reward / Unit</LearnTooltip>}
                      value={intel.rewardPerUnit.toFixed(5)}
                      mono
                    />
                    <IntelligenceRow
                      label={<LearnTooltip explain={{ beginner: "The total dollar amount you risk on this trade if stopped out.", intermediate: "Risk notional = risk/unit × qty. Your max loss on this position.", experienced: "Dollar risk = (fill − stop) × qty.", expert: "Max adverse excursion at stop." }}>Risk Notional</LearnTooltip>}
                      value={`$${intel.riskNotional.toFixed(2)}`}
                      mono
                    />
                    <IntelligenceRow
                      label={<LearnTooltip explain={{ beginner: "The total dollar amount you could gain if the target is hit.", intermediate: "Reward notional = reward/unit × qty. Your max gain on this position.", experienced: "Dollar reward = (target − fill) × qty.", expert: "Max favorable excursion at target." }}>Reward Notional</LearnTooltip>}
                      value={`$${intel.rewardNotional.toFixed(2)}`}
                      mono
                    />
                    <IntelligenceRow
                      label={<LearnTooltip explain={{ beginner: "How far your stop is from your entry price, as a percentage. Smaller = tighter stop.", intermediate: "Stop distance % = (fill − stop) / fill × 100.", experienced: "Stop distance as % of entry. Used to assess position sensitivity.", expert: "stop_dist_pct = |fill − stop| / fill × 100" }}>Stop Distance</LearnTooltip>}
                      value={`${intel.stopDistancePct.toFixed(3)}%`}
                      mono
                    />
                    <IntelligenceRow
                      label={<LearnTooltip explain={{ beginner: "How far your target is from your entry price, as a percentage.", intermediate: "Target distance % = (target − fill) / fill × 100.", experienced: "Target move required to close profitably.", expert: "target_dist_pct = |target − fill| / fill × 100" }}>Target Distance</LearnTooltip>}
                      value={`${intel.targetDistancePct.toFixed(3)}%`}
                      mono
                    />
                  </div>

                  {detail.reason ? (
                    <div className={styles.reasonBox}>
                      <p className={styles.reasonLabel}>Reason</p>
                      <p className={styles.reasonText}>{detail.reason}</p>
                    </div>
                  ) : null}
                </div>
              );
            })() : null}
          </div>

          {/* Journal panel */}
          <div className={styles.panel}>
            <ExecutionJournalPanel detail={detail} selectedExecutionId={selectedExecutionId} />
          </div>
        </section>
      </div>
    </main>
  );
}

export default function ExecutionPage() {
  return (
    <Suspense fallback={null}>
      <ExecutionPageContent />
    </Suspense>
  );
}