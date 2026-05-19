"use client";

import { useCallback, useEffect, useState } from "react";

import {
  getDataQualityOutliers,
  reviewDataQualityOutlier,
  getDataQualityAuditTrail,
} from "../../lib/api/researchData";
import type {
  DataQualityAuditEntry,
  DataQualityOutlierItem,
  DataQualityReviewStatus,
} from "../../lib/types";
import styles from "../../styles/pages/data-quality.module.css";

const REVIEW_STATUS_LABELS: Record<DataQualityReviewStatus, string> = {
  unreviewed: "Unreviewed",
  valid_market_move: "Valid Market Move",
  bad_data: "Bad Data",
  needs_provider_check: "Needs Provider Check",
  ignore_for_now: "Ignore for Now",
};

const REVIEW_STATUS_OPTIONS: DataQualityReviewStatus[] = [
  "unreviewed",
  "valid_market_move",
  "bad_data",
  "needs_provider_check",
  "ignore_for_now",
];

const QUICK_ACTIONS: { status: DataQualityReviewStatus; label: string }[] = [
  { status: "valid_market_move", label: "✓ Valid" },
  { status: "bad_data", label: "✗ Bad Data" },
  { status: "needs_provider_check", label: "? Provider" },
  { status: "ignore_for_now", label: "– Ignore" },
];

function statusBadgeClass(status: DataQualityReviewStatus): string {
  if (status === "unreviewed") return styles.badgeUnreviewed;
  if (status === "valid_market_move") return styles.badgeValid;
  if (status === "bad_data") return styles.badgeBad;
  if (status === "needs_provider_check") return styles.badgeProvider;
  return styles.badgeIgnore;
}

function fmt(value: number | null, decimals = 1): string {
  if (value === null || value === undefined) return "–";
  return value.toFixed(decimals);
}

function fmtDate(iso: string | null): string {
  if (!iso) return "–";
  return new Date(iso).toLocaleString();
}

export default function DataQualityPage() {
  const [outliers, setOutliers] = useState<DataQualityOutlierItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [filterAsset, setFilterAsset] = useState("");
  const [filterProvider, setFilterProvider] = useState("");
  const [filterTimeframe, setFilterTimeframe] = useState("");

  // Selected item + inline review form
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [reviewStatus, setReviewStatus] = useState<DataQualityReviewStatus>("unreviewed");
  const [reviewNotes, setReviewNotes] = useState("");
  const [reviewedBy, setReviewedBy] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitMsg, setSubmitMsg] = useState<string | null>(null);

  // Audit trail
  const [auditEntries, setAuditEntries] = useState<DataQualityAuditEntry[]>([]);
  const [auditOpen, setAuditOpen] = useState(false);
  const [auditLoading, setAuditLoading] = useState(false);

  const loadOutliers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await getDataQualityOutliers({
        reviewStatus: filterStatus || undefined,
        asset: filterAsset.trim() || undefined,
        provider: filterProvider.trim() || undefined,
        timeframe: filterTimeframe.trim() || undefined,
      });
      setOutliers(resp.items);
      setTotal(resp.total);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load outliers");
    } finally {
      setLoading(false);
    }
  }, [filterStatus, filterAsset, filterProvider, filterTimeframe]);

  useEffect(() => {
    void loadOutliers();
  }, [loadOutliers]);

  async function loadAuditTrail(reportId: string) {
    setAuditLoading(true);
    try {
      const resp = await getDataQualityAuditTrail(reportId);
      setAuditEntries(resp.entries);
    } catch {
      setAuditEntries([]);
    } finally {
      setAuditLoading(false);
    }
  }

  function selectRow(item: DataQualityOutlierItem) {
    setSelectedId(item.id);
    setReviewStatus(item.review_status);
    setReviewNotes(item.review_notes ?? "");
    setReviewedBy("");
    setSubmitMsg(null);
    setAuditEntries([]);
    setAuditOpen(false);
  }

  async function handleReviewSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedId) return;
    setSubmitting(true);
    setSubmitMsg(null);
    try {
      await reviewDataQualityOutlier(selectedId, {
        review_status: reviewStatus,
        review_notes: reviewNotes.trim() || null,
        reviewed_by: reviewedBy.trim() || null,
      });
      setSubmitMsg("Saved");
      await loadOutliers();
      if (auditOpen) await loadAuditTrail(selectedId);
    } catch (err: unknown) {
      setSubmitMsg(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleQuickAction(status: DataQualityReviewStatus) {
    if (!selectedId) return;
    setSubmitting(true);
    setSubmitMsg(null);
    try {
      await reviewDataQualityOutlier(selectedId, {
        review_status: status,
        review_notes: null,
        reviewed_by: reviewedBy.trim() || null,
      });
      setReviewStatus(status);
      setSubmitMsg("Saved");
      await loadOutliers();
      if (auditOpen) await loadAuditTrail(selectedId);
    } catch (err: unknown) {
      setSubmitMsg(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function toggleAuditTrail() {
    if (!selectedId) return;
    const next = !auditOpen;
    setAuditOpen(next);
    if (next && auditEntries.length === 0) {
      await loadAuditTrail(selectedId);
    }
  }

  const selectedItem = outliers.find((o) => o.id === selectedId) ?? null;

  return (
    <div className={styles.page}>
      <div className={styles.container}>
        {/* Header */}
        <div className={styles.header}>
          <div>
            <h1 className={styles.title}>Data Quality Review</h1>
            <p className={styles.subtitle}>
              Inspect flagged outliers and assign a triage status to each item.
            </p>
          </div>
          <span className={styles.badge}>MH-13</span>
        </div>

        {/* Error banner */}
        {error && <div className={styles.errorBanner}>{error}</div>}

        {/* Filter bar */}
        <div className={styles.filterBar} data-testid="dq-filter-bar">
          <label className={styles.filterLabel}>
            Status
            <select
              className={styles.select}
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
            >
              <option value="">All</option>
              {REVIEW_STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {REVIEW_STATUS_LABELS[s]}
                </option>
              ))}
            </select>
          </label>
          <label className={styles.filterLabel}>
            Asset
            <input
              className={styles.input}
              value={filterAsset}
              onChange={(e) => setFilterAsset(e.target.value)}
              placeholder="e.g. AAPL"
              data-testid="dq-filter-asset"
            />
          </label>
          <label className={styles.filterLabel}>
            Provider
            <input
              className={styles.input}
              value={filterProvider}
              onChange={(e) => setFilterProvider(e.target.value)}
              placeholder="e.g. yfinance"
              data-testid="dq-filter-provider"
            />
          </label>
          <label className={styles.filterLabel}>
            Timeframe
            <input
              className={styles.input}
              value={filterTimeframe}
              onChange={(e) => setFilterTimeframe(e.target.value)}
              placeholder="e.g. 1d"
              data-testid="dq-filter-timeframe"
            />
          </label>
          <span className={styles.countBadge}>
            {loading ? "Loading…" : `${total} flagged item${total !== 1 ? "s" : ""}`}
          </span>
        </div>

        {/* Two-column layout: list + detail */}
        <div className={styles.splitLayout}>
          {/* Outlier list */}
          <section className={styles.listPanel} data-testid="dq-outlier-list">
            {loading && <p className={styles.muted}>Loading…</p>}
            {!loading && outliers.length === 0 && (
              <p className={styles.muted}>No flagged outliers found.</p>
            )}
            {!loading && outliers.length > 0 && (
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th className={styles.th}>Asset</th>
                    <th className={styles.th}>TF</th>
                    <th className={styles.th}>Score</th>
                    <th className={styles.th}>Spikes</th>
                    <th className={styles.th}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {outliers.map((item) => (
                    <tr
                      key={item.id}
                      className={
                        item.id === selectedId
                          ? `${styles.tr} ${styles.trSelected}`
                          : styles.tr
                      }
                      onClick={() => selectRow(item)}
                    >
                      <td className={styles.td}>{item.asset_symbol}</td>
                      <td className={styles.td}>{item.timeframe}</td>
                      <td className={styles.td}>{fmt(item.quality_score)}</td>
                      <td className={styles.td}>{item.suspicious_spike_bars}</td>
                      <td className={styles.td}>
                        <span className={statusBadgeClass(item.review_status)}>
                          {REVIEW_STATUS_LABELS[item.review_status]}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          {/* Detail / review panel */}
          <section className={styles.detailPanel} data-testid="dq-detail-panel">
            {!selectedItem && (
              <p className={styles.muted}>Select an item to review it.</p>
            )}
            {selectedItem && (
              <>
                <h2 className={styles.detailTitle}>
                  {selectedItem.asset_symbol} / {selectedItem.timeframe}
                </h2>

                {/* Metrics grid */}
                <div className={styles.metricsGrid} data-testid="dq-metrics-grid">
                  <div className={styles.metric}>
                    <span className={styles.metricLabel}>Quality Score</span>
                    <span className={styles.metricValue}>
                      {fmt(selectedItem.quality_score)}
                    </span>
                  </div>
                  <div className={styles.metric}>
                    <span className={styles.metricLabel}>Approved</span>
                    <span className={styles.metricValue}>
                      {selectedItem.approved_for_backtest ? "Yes" : "No"}
                    </span>
                  </div>
                  <div className={styles.metric}>
                    <span className={styles.metricLabel}>Spike Bars</span>
                    <span className={styles.metricValue}>
                      {selectedItem.suspicious_spike_bars}
                    </span>
                  </div>
                  <div className={styles.metric}>
                    <span className={styles.metricLabel}>Bad Price Bars</span>
                    <span className={styles.metricValue}>
                      {selectedItem.bad_price_bars}
                    </span>
                  </div>
                  <div className={styles.metric}>
                    <span className={styles.metricLabel}>Missing Bars</span>
                    <span className={styles.metricValue}>
                      {selectedItem.missing_bars}
                    </span>
                  </div>
                  <div className={styles.metric}>
                    <span className={styles.metricLabel}>Completeness</span>
                    <span className={styles.metricValue}>
                      {fmt(selectedItem.completeness_pct)}%
                    </span>
                  </div>
                  <div className={styles.metric}>
                    <span className={styles.metricLabel}>Total Bars</span>
                    <span className={styles.metricValue}>
                      {selectedItem.total_bars.toLocaleString()}
                    </span>
                  </div>
                  <div className={styles.metric}>
                    <span className={styles.metricLabel}>Provider</span>
                    <span className={styles.metricValue}>
                      {selectedItem.provider ?? "–"}
                    </span>
                  </div>
                  {selectedItem.reviewed_by && (
                    <div className={styles.metric}>
                      <span className={styles.metricLabel}>Reviewed by</span>
                      <span className={styles.metricValue}>{selectedItem.reviewed_by}</span>
                    </div>
                  )}
                  {selectedItem.reviewed_at && (
                    <div className={styles.metric}>
                      <span className={styles.metricLabel}>Reviewed at</span>
                      <span className={styles.metricValue}>{fmtDate(selectedItem.reviewed_at)}</span>
                    </div>
                  )}
                </div>

                {/* Quick actions */}
                <div className={styles.quickActions} data-testid="dq-quick-actions">
                  {QUICK_ACTIONS.map(({ status, label }) => (
                    <button
                      key={status}
                      type="button"
                      className={styles.btnQuick}
                      onClick={() => void handleQuickAction(status)}
                      disabled={submitting}
                    >
                      {label}
                    </button>
                  ))}
                </div>

                {/* Review form */}
                <form
                  className={styles.reviewForm}
                  onSubmit={(e) => void handleReviewSubmit(e)}
                  data-testid="dq-review-form"
                >
                  <h3 className={styles.reviewFormTitle}>Triage Decision</h3>
                  <label className={styles.label}>
                    Status
                    <select
                      className={styles.select}
                      value={reviewStatus}
                      onChange={(e) =>
                        setReviewStatus(e.target.value as DataQualityReviewStatus)
                      }
                    >
                      {REVIEW_STATUS_OPTIONS.map((s) => (
                        <option key={s} value={s}>
                          {REVIEW_STATUS_LABELS[s]}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className={styles.label}>
                    Reviewed by (optional)
                    <input
                      className={styles.input}
                      value={reviewedBy}
                      onChange={(e) => setReviewedBy(e.target.value)}
                      placeholder="Your name or username"
                      maxLength={255}
                      data-testid="dq-reviewed-by"
                    />
                  </label>
                  <label className={styles.label}>
                    Notes (optional)
                    <textarea
                      className={styles.textarea}
                      value={reviewNotes}
                      onChange={(e) => setReviewNotes(e.target.value)}
                      rows={3}
                      maxLength={2000}
                      placeholder="Explain the triage decision…"
                    />
                  </label>
                  <div className={styles.formActions}>
                    <button
                      type="submit"
                      className={styles.btnPrimary}
                      disabled={submitting}
                    >
                      {submitting ? "Saving…" : "Save Review"}
                    </button>
                    {submitMsg && (
                      <span className={styles.submitMsg}>{submitMsg}</span>
                    )}
                  </div>
                </form>

                {/* Audit trail */}
                <div className={styles.auditSection} data-testid="dq-audit-section">
                  <button
                    type="button"
                    className={styles.auditToggle}
                    onClick={() => void toggleAuditTrail()}
                  >
                    {auditOpen ? "▼" : "▶"} Review history
                  </button>
                  {auditOpen && (
                    <div className={styles.auditList}>
                      {auditLoading && <p className={styles.muted}>Loading…</p>}
                      {!auditLoading && auditEntries.length === 0 && (
                        <p className={styles.muted}>No prior reviews recorded.</p>
                      )}
                      {!auditLoading &&
                        auditEntries.map((entry) => (
                          <div key={entry.id} className={styles.auditEntry}>
                            <span className={styles.auditStatus}>{entry.new_status}</span>
                            {entry.reviewed_by && (
                              <span className={styles.auditMeta}>by {entry.reviewed_by}</span>
                            )}
                            <span className={styles.auditMeta}>{fmtDate(entry.reviewed_at)}</span>
                            {entry.review_notes && (
                              <p className={styles.auditNotes}>{entry.review_notes}</p>
                            )}
                          </div>
                        ))}
                    </div>
                  )}
                </div>
              </>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
