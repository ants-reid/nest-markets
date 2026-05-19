"use client";

import styles from "../../styles/pages/broker.module.css";
import type {
  BackupPackDetailSection,
  BackupPackSummary,
  BackupPackViewModel,
  ChecklistItemStatus,
  CopyState,
  ReadinessBackupPack,
  ReadinessChecklistItem,
  ReadinessComparisonChange,
  ReadinessSnapshot,
  TimelinePoint,
} from "./review-helpers";

type SharedFormattingProps = {
  formatTimestamp: (value: string) => string;
  getStatusClassName: (status: ChecklistItemStatus) => string;
  getStatusLabel: (status: ChecklistItemStatus) => string;
};

export function ReadinessChecklistItemsList({
  items,
  getStatusClassName,
  getStatusLabel,
}: {
  items: ReadinessChecklistItem[];
  getStatusClassName: SharedFormattingProps["getStatusClassName"];
  getStatusLabel: SharedFormattingProps["getStatusLabel"];
}) {
  return (
    <div className={styles.readinessList}>
      {items.map((item) => (
        <div
          key={item.id}
          className={styles.readinessItem}
          data-testid={`broker-readiness-item-${item.id}`}
        >
          <span className={`${styles.readinessItemStatus} ${getStatusClassName(item.status)}`}>
            {getStatusLabel(item.status)}
          </span>
          <div className={styles.readinessItemBody}>
            <span className={styles.readinessItemLabel}>{item.label}</span>
            <span className={styles.readinessItemDetail}>{item.detail}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

export function BackupPackSummaryPanel({
  summary,
  formatTimestamp,
}: {
  summary: BackupPackSummary;
  formatTimestamp: SharedFormattingProps["formatTimestamp"];
}) {
  return (
    <div className={styles.backupPackSummaryPanel} data-testid="broker-readiness-backup-pack-summary">
      <div className={styles.backupPackSummaryHeader}>
        <span className={styles.readinessHistoryTitle}>Backup Pack Summary</span>
        <span className={styles.readinessHistoryMeta} data-testid="broker-readiness-backup-pack-summary-source">
          {summary.source === "export" ? "Last exported backup pack" : "Last imported backup pack"}
        </span>
      </div>
      <div className={styles.backupPackSummaryGrid}>
        <div className={styles.backupPackSummaryCard} data-testid="broker-readiness-backup-pack-summary-snapshots">
          <span className={styles.backupPackSummaryLabel}>Readiness snapshots</span>
          <span className={styles.backupPackSummaryValue}>{summary.snapshotCount}</span>
        </div>
        <div className={styles.backupPackSummaryCard} data-testid="broker-readiness-backup-pack-summary-provenance">
          <span className={styles.backupPackSummaryLabel}>Provenance rows</span>
          <span className={styles.backupPackSummaryValue}>{summary.provenanceRowCount}</span>
        </div>
        <div className={styles.backupPackSummaryCard} data-testid="broker-readiness-backup-pack-summary-audit">
          <span className={styles.backupPackSummaryLabel}>Audit rows</span>
          <span className={styles.backupPackSummaryValue}>{summary.auditRowCount}</span>
        </div>
      </div>
      <div className={styles.backupPackSummaryMeta}>
        <span data-testid="broker-readiness-backup-pack-summary-exported-at">Exported: {formatTimestamp(summary.exportedAt)}</span>
        <span data-testid="broker-readiness-backup-pack-summary-account">Account: {summary.accountId ?? "—"}</span>
        <span data-testid="broker-readiness-backup-pack-summary-mode">Mode: {summary.brokerMode ?? "—"}</span>
      </div>
    </div>
  );
}

function BackupPackReportPanel({
  detail,
  view,
  formatTimestamp,
}: {
  detail: ReadinessBackupPack;
  view: BackupPackViewModel;
  formatTimestamp: SharedFormattingProps["formatTimestamp"];
}) {
  return (
    <div className={styles.backupPackReportPanel} data-testid="broker-readiness-backup-pack-report">
      <div className={styles.backupPackReportHeader}>
        <div>
          <span className={styles.readinessHistoryTitle}>Backup Pack Human Review Report</span>
          <p className={styles.backupPackDetailDescription}>
            Print-friendly local review summary generated from the selected backup pack payload.
          </p>
        </div>
        <span className={styles.readinessHistoryMeta} data-testid="broker-readiness-backup-pack-report-generated-at">
          Generated: {formatTimestamp(detail.exported_at)}
        </span>
      </div>
      <div className={styles.backupPackReportMeta}>
        <span data-testid="broker-readiness-backup-pack-report-account">Account: {detail.metadata?.account_id ?? "—"}</span>
        <span data-testid="broker-readiness-backup-pack-report-mode">Mode: {detail.metadata?.broker_mode ?? "—"}</span>
        <span data-testid="broker-readiness-backup-pack-report-source">Source: {view.sourceLabel}</span>
      </div>
      <div className={styles.backupPackReportGrid}>
        <section className={styles.backupPackReportCard} data-testid="broker-readiness-backup-pack-report-readiness">
          <span className={styles.backupPackSummaryLabel}>Readiness summary</span>
          <p className={styles.backupPackReportText}>
            Current baseline: {view.currentSnapshot?.ready_count ?? 0}/{view.currentSnapshot?.total_count ?? 0} ready.
            Ready {view.currentCounts.ready} · Advisory {view.currentCounts.advisory} · Missing {view.currentCounts.missing}.
          </p>
        </section>
        <section className={styles.backupPackReportCard} data-testid="broker-readiness-backup-pack-report-snapshots">
          <span className={styles.backupPackSummaryLabel}>Snapshots summary</span>
          <p className={styles.backupPackReportText}>
            {view.snapshotHistory.length} saved snapshot{view.snapshotHistory.length === 1 ? "" : "s"} in pack.
            Average saved readiness score {view.snapshotAverageReady}%.
          </p>
        </section>
        <section className={styles.backupPackReportCard} data-testid="broker-readiness-backup-pack-report-provenance">
          <span className={styles.backupPackSummaryLabel}>Provenance summary</span>
          <p className={styles.backupPackReportText}>
            {view.provenanceRows.length} provenance row{view.provenanceRows.length === 1 ? "" : "s"} across {view.provenanceSymbolCount} symbol{view.provenanceSymbolCount === 1 ? "" : "s"}.
            {" "}Realized P&amp;L present on {view.provenancePnlPresentCount} row{view.provenancePnlPresentCount === 1 ? "" : "s"}.
          </p>
        </section>
        <section className={styles.backupPackReportCard} data-testid="broker-readiness-backup-pack-report-audit">
          <span className={styles.backupPackSummaryLabel}>Audit summary</span>
          <p className={styles.backupPackReportText}>
            {view.auditRows.length} audit row{view.auditRows.length === 1 ? "" : "s"}.
            {" "}Dry run {view.auditDryRunCount} · Submit {view.auditSubmitCount} · Rows with issues {view.auditIssueCount}.
          </p>
        </section>
      </div>
      <div className={styles.backupPackReportFooter} data-testid="broker-readiness-backup-pack-report-footer">
        Local-only review artifact generated from {detail.format} at {formatTimestamp(detail.exported_at)}.
      </div>
    </div>
  );
}

export function BackupPackDetailViewer({
  detail,
  section,
  view,
  detailCopyState,
  reportCopyState,
  onSelectSection,
  onCopyReport,
  onExportReport,
  onCopySection,
  onExportSection,
  onPrintReport,
  formatTimestamp,
  getSectionLabel,
}: {
  detail: ReadinessBackupPack;
  section: BackupPackDetailSection;
  view: BackupPackViewModel;
  detailCopyState: CopyState;
  reportCopyState: CopyState;
  onSelectSection: (section: BackupPackDetailSection) => void;
  onCopyReport: () => void;
  onExportReport: (extension: "txt" | "md", mimeType: string) => void;
  onCopySection: () => void;
  onExportSection: () => void;
  onPrintReport: () => void;
  formatTimestamp: SharedFormattingProps["formatTimestamp"];
  getSectionLabel: (section: BackupPackDetailSection) => string;
}) {
  return (
    <div className={styles.backupPackDetailPanel} data-testid="broker-readiness-backup-pack-detail">
      <div className={styles.backupPackDetailHeader}>
        <div>
          <span className={styles.readinessHistoryTitle}>Backup Pack Detail Viewer</span>
          <p className={styles.backupPackDetailDescription}>
            Read-only view of the last exported or imported local backup pack payload.
          </p>
        </div>
        <span className={styles.readinessHistoryMeta} data-testid="broker-readiness-backup-pack-detail-exported-at">
          Generated: {formatTimestamp(detail.exported_at)}
        </span>
      </div>
      <div className={styles.backupPackDetailSectionTabs}>
        {(["snapshots", "provenance", "audit"] as BackupPackDetailSection[]).map((nextSection) => (
          <button
            key={nextSection}
            type="button"
            className={`${styles.backupPackDetailSectionTab} ${section === nextSection ? styles.backupPackDetailSectionTabActive : ""}`}
            onClick={() => onSelectSection(nextSection)}
            data-testid={`broker-readiness-backup-pack-detail-section-${nextSection}`}
          >
            {getSectionLabel(nextSection)}
          </button>
        ))}
      </div>
      <div className={styles.backupPackDetailToolbar}>
        <span className={styles.readinessHistoryMeta} data-testid="broker-readiness-backup-pack-detail-section-meta">
          {view.sectionMeta}
        </span>
        <div className={styles.backupPackDetailActions}>
          <button
            type="button"
            className={`${styles.secondaryButton} ${styles.readinessActionButton}`}
            onClick={onCopyReport}
            data-testid="broker-readiness-backup-pack-report-copy"
          >
            Copy Full Report
          </button>
          <button
            type="button"
            className={`${styles.secondaryButton} ${styles.readinessActionButton}`}
            onClick={() => onExportReport("md", "text/markdown;charset=utf-8")}
            data-testid="broker-readiness-backup-pack-report-export-md"
          >
            Export Markdown
          </button>
          <button
            type="button"
            className={`${styles.secondaryButton} ${styles.readinessActionButton}`}
            onClick={() => onExportReport("txt", "text/plain;charset=utf-8")}
            data-testid="broker-readiness-backup-pack-report-export-txt"
          >
            Export Text
          </button>
          <button
            type="button"
            className={`${styles.secondaryButton} ${styles.readinessActionButton}`}
            onClick={onCopySection}
            data-testid="broker-readiness-backup-pack-detail-copy-selected"
          >
            Copy Selected Section
          </button>
          <button
            type="button"
            className={`${styles.secondaryButton} ${styles.readinessActionButton}`}
            onClick={onExportSection}
            data-testid="broker-readiness-backup-pack-detail-export-selected"
          >
            Export Selected Section
          </button>
          <button
            type="button"
            className={`${styles.secondaryButton} ${styles.readinessActionButton} ${styles.readinessPrintButton}`}
            onClick={onPrintReport}
            data-testid="broker-readiness-backup-pack-report-print"
          >
            Print Review Report
          </button>
        </div>
      </div>
      {detailCopyState === "copied" && (
        <div className={styles.readinessCopyState} data-testid="broker-readiness-backup-pack-detail-copy-state">Copied selected backup pack section.</div>
      )}
      {detailCopyState === "error" && (
        <div className={styles.readinessCopyStateError} data-testid="broker-readiness-backup-pack-detail-copy-state">Clipboard unavailable.</div>
      )}
      {reportCopyState === "copied" && (
        <div className={styles.readinessCopyState} data-testid="broker-readiness-backup-pack-report-copy-state">Copied full backup pack report.</div>
      )}
      {reportCopyState === "error" && (
        <div className={styles.readinessCopyStateError} data-testid="broker-readiness-backup-pack-report-copy-state">Clipboard unavailable.</div>
      )}
      <BackupPackReportPanel detail={detail} view={view} formatTimestamp={formatTimestamp} />
      {section === "snapshots" && (
        <div className={styles.backupPackDetailSectionBody} data-testid="broker-readiness-backup-pack-detail-snapshots">
          <div className={styles.backupPackDetailSnapshotCurrent} data-testid="broker-readiness-backup-pack-current-snapshot">
            <div className={styles.backupPackDetailItemHeader}>
              <span className={styles.backupPackDetailItemTitle}>Current readiness snapshot</span>
              <span className={styles.backupPackDetailItemMeta}>
                {view.currentSnapshot?.ready_count ?? 0}/{view.currentSnapshot?.total_count ?? 0} ready
              </span>
            </div>
            <p className={styles.backupPackDetailItemSummary}>
              {view.currentSnapshot?.summary_text.split("\n")[0] ?? "No current readiness snapshot included."}
            </p>
            <span className={styles.backupPackDetailItemMeta}>
              Captured {view.currentSnapshot ? formatTimestamp(view.currentSnapshot.captured_at) : "—"}
            </span>
          </div>
          {view.snapshotHistory.length === 0 ? (
            <p className={styles.readinessHistoryEmpty} data-testid="broker-readiness-backup-pack-snapshots-empty">
              No saved readiness history snapshots were included in this pack.
            </p>
          ) : (
            <div className={styles.backupPackDetailList}>
              {view.snapshotHistory.map((snapshot) => (
                <div
                  key={snapshot.id}
                  className={styles.backupPackDetailItem}
                  data-testid="broker-readiness-backup-pack-snapshot-item"
                >
                  <div className={styles.backupPackDetailItemHeader}>
                    <span className={styles.backupPackDetailItemTitle}>{formatTimestamp(snapshot.captured_at)}</span>
                    <span className={styles.backupPackDetailItemMeta}>{snapshot.ready_count}/{snapshot.total_count} ready</span>
                  </div>
                  <p className={styles.backupPackDetailItemSummary}>{snapshot.summary_text.split("\n")[0]}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      {section === "provenance" && (
        <div className={styles.backupPackDetailSectionBody} data-testid="broker-readiness-backup-pack-detail-provenance">
          {view.provenanceRows.length === 0 ? (
            <p className={styles.readinessHistoryEmpty} data-testid="broker-readiness-backup-pack-provenance-empty">
              No provenance rows were included in this pack.
            </p>
          ) : (
            <div className={styles.backupPackDetailList}>
              {view.provenanceRows.map((row) => (
                <div
                  key={row.event_fingerprint}
                  className={styles.backupPackDetailItem}
                  data-testid="broker-readiness-backup-pack-provenance-row"
                >
                  <div className={styles.backupPackDetailItemHeader}>
                    <span className={styles.backupPackDetailItemTitle}>
                      {row.symbol ?? "Unknown symbol"} {row.side ?? ""}
                    </span>
                    <span className={styles.backupPackDetailItemMeta}>{row.source}</span>
                  </div>
                  <p className={styles.backupPackDetailItemSummary}>
                    Qty {row.quantity ?? "—"} · Realized P&amp;L {row.realized_pnl ?? "—"} · Account {row.account_id ?? "—"}
                  </p>
                  <span className={styles.backupPackDetailItemMeta}>Captured {formatTimestamp(row.created_at)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      {section === "audit" && (
        <div className={styles.backupPackDetailSectionBody} data-testid="broker-readiness-backup-pack-detail-audit">
          {view.auditRows.length === 0 ? (
            <p className={styles.readinessHistoryEmpty} data-testid="broker-readiness-backup-pack-audit-empty">
              No audit rows were included in this pack.
            </p>
          ) : (
            <div className={styles.backupPackDetailList}>
              {view.auditRows.map((entry, index) => (
                <div
                  key={`${entry.ts}-${entry.event}-${index}`}
                  className={styles.backupPackDetailItem}
                  data-testid="broker-readiness-backup-pack-audit-row"
                >
                  <div className={styles.backupPackDetailItemHeader}>
                    <span className={styles.backupPackDetailItemTitle}>{entry.event} · {entry.action}</span>
                    <span className={styles.backupPackDetailItemMeta}>{entry.status}</span>
                  </div>
                  <p className={styles.backupPackDetailItemSummary}>
                    {entry.ticker} {entry.side} · Qty {entry.quantity ?? "—"} · {entry.dry_run ? "Dry run" : "Submit"}
                  </p>
                  <span className={styles.backupPackDetailItemMeta}>
                    {formatTimestamp(entry.ts)} · Issues {entry.issues.length}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function ReadinessSavedHistorySection({
  history,
  selectedSnapshot,
  onSelectSnapshot,
  latestSnapshot,
  compareSnapshot,
  compareCounts,
  latestCounts,
  changedComparisonItems,
  timelineSnapshots,
  timelineSnapshot,
  timelinePoints,
  timelinePath,
  timelineChartWidth,
  timelineChartHeight,
  timelinePadX,
  timelinePadY,
  onSelectTimelineSnapshot,
  formatTimestamp,
  getStatusLabel,
  summarizeSnapshotCounts,
}: {
  history: ReadinessSnapshot[];
  selectedSnapshot: ReadinessSnapshot | null;
  onSelectSnapshot: (snapshotId: string) => void;
  latestSnapshot: ReadinessSnapshot | null;
  compareSnapshot: ReadinessSnapshot | null;
  compareCounts: Record<ChecklistItemStatus, number>;
  latestCounts: Record<ChecklistItemStatus, number>;
  changedComparisonItems: ReadinessComparisonChange[];
  timelineSnapshots: ReadinessSnapshot[];
  timelineSnapshot: ReadinessSnapshot | null;
  timelinePoints: TimelinePoint[];
  timelinePath: string;
  timelineChartWidth: number;
  timelineChartHeight: number;
  timelinePadX: number;
  timelinePadY: number;
  onSelectTimelineSnapshot: (snapshotId: string) => void;
  formatTimestamp: SharedFormattingProps["formatTimestamp"];
  getStatusLabel: SharedFormattingProps["getStatusLabel"];
  summarizeSnapshotCounts: (snapshot: ReadinessSnapshot) => Record<ChecklistItemStatus, number>;
}) {
  if (history.length === 0) {
    return (
      <p className={styles.readinessHistoryEmpty} data-testid="broker-readiness-history-empty">
        No local readiness snapshots saved yet.
      </p>
    );
  }

  return (
    <>
      <div className={styles.readinessHistoryList}>
        {history.map((snapshot, index) => (
          <button
            key={snapshot.id}
            type="button"
            className={`${styles.readinessHistoryItem} ${selectedSnapshot?.id === snapshot.id ? styles.readinessHistoryItemSelected : ""}`}
            data-testid="broker-readiness-history-item"
            onClick={() => onSelectSnapshot(snapshot.id)}
          >
            <div className={styles.readinessHistoryItemHeader}>
              <span className={styles.readinessHistoryTimestamp}>{formatTimestamp(snapshot.captured_at)}</span>
              <span className={styles.readinessHistoryReadyCount}>{snapshot.ready_count}/{snapshot.total_count} ready</span>
            </div>
            <p className={styles.readinessHistorySummary}>{snapshot.summary_text.split("\n")[0]}</p>
            <span className={styles.readinessHistoryTag}>{index === 0 ? "Latest baseline" : "Compare target"}</span>
          </button>
        ))}
      </div>

      <div className={styles.readinessComparePanel} data-testid="broker-readiness-compare-panel">
        <div className={styles.readinessCompareHeader}>
          <span className={styles.readinessCompareTitle}>Readiness Compare View</span>
          {compareSnapshot !== null && latestSnapshot !== null ? (
            <span className={styles.readinessCompareMeta} data-testid="broker-readiness-compare-range">
              {formatTimestamp(compareSnapshot.captured_at)} {" -> "} {formatTimestamp(latestSnapshot.captured_at)}
            </span>
          ) : (
            <span className={styles.readinessCompareMeta} data-testid="broker-readiness-compare-range">
              Select an older saved snapshot to compare against the latest baseline.
            </span>
          )}
        </div>

        {compareSnapshot !== null && latestSnapshot !== null ? (
          <>
            <div className={styles.readinessCompareCounts}>
              <div className={styles.readinessCompareCountCard} data-testid="broker-readiness-compare-ready-count">
                <span className={styles.readinessCompareCountLabel}>Ready</span>
                <span className={styles.readinessCompareCountValue}>{compareCounts.ready} {" -> "} {latestCounts.ready}</span>
              </div>
              <div className={styles.readinessCompareCountCard} data-testid="broker-readiness-compare-advisory-count">
                <span className={styles.readinessCompareCountLabel}>Advisory</span>
                <span className={styles.readinessCompareCountValue}>{compareCounts.advisory} {" -> "} {latestCounts.advisory}</span>
              </div>
              <div className={styles.readinessCompareCountCard} data-testid="broker-readiness-compare-missing-count">
                <span className={styles.readinessCompareCountLabel}>Missing</span>
                <span className={styles.readinessCompareCountValue}>{compareCounts.missing} {" -> "} {latestCounts.missing}</span>
              </div>
            </div>

            {changedComparisonItems.length > 0 ? (
              <div className={styles.readinessCompareChanges}>
                {changedComparisonItems.map((item) => (
                  <div
                    key={item.id}
                    className={styles.readinessCompareChangeItem}
                    data-testid="broker-readiness-compare-change-item"
                  >
                    <div className={styles.readinessCompareChangeHeader}>
                      <span className={styles.readinessCompareChangeLabel}>{item.label}</span>
                      <span
                        className={item.changeType === "improved" ? styles.readinessCompareImproved : styles.readinessCompareRegressed}
                        data-testid={`broker-readiness-compare-change-${item.changeType}`}
                      >
                        {item.changeType === "improved" ? "Improved" : "Regressed"}
                      </span>
                    </div>
                    <p className={styles.readinessCompareChangeDetail}>
                      {getStatusLabel(item.previousStatus)} {" -> "} {getStatusLabel(item.currentStatus)}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className={styles.readinessHistoryEmpty} data-testid="broker-readiness-compare-no-changes">
                No readiness item status changes between the selected snapshot and the latest baseline.
              </p>
            )}
          </>
        ) : null}
      </div>

      <div className={styles.readinessTimelinePanel} data-testid="broker-readiness-timeline-panel">
        <div className={styles.readinessTimelineHeader}>
          <span className={styles.readinessCompareTitle}>Readiness Timeline</span>
          <span className={styles.readinessCompareMeta}>Local snapshots only</span>
        </div>

        <div className={styles.readinessTimelineChartWrap}>
          <svg
            className={styles.readinessTimelineChart}
            viewBox={`0 0 ${timelineChartWidth} ${timelineChartHeight}`}
            role="img"
            aria-label="Broker readiness score trend"
          >
            <line
              x1={timelinePadX}
              y1={timelineChartHeight - timelinePadY}
              x2={timelineChartWidth - timelinePadX}
              y2={timelineChartHeight - timelinePadY}
              className={styles.readinessTimelineAxis}
            />
            <line
              x1={timelinePadX}
              y1={timelinePadY}
              x2={timelinePadX}
              y2={timelineChartHeight - timelinePadY}
              className={styles.readinessTimelineAxis}
            />
            {timelinePoints.length > 1 ? (
              <polyline
                points={timelinePath}
                fill="none"
                className={styles.readinessTimelineLine}
                data-testid="broker-readiness-timeline-line"
              />
            ) : timelinePoints.length === 1 ? (
              <line
                x1={timelinePoints[0].x - 10}
                y1={timelinePoints[0].y - 3}
                x2={timelinePoints[0].x + 10}
                y2={timelinePoints[0].y + 3}
                className={styles.readinessTimelineLine}
                data-testid="broker-readiness-timeline-line"
              />
            ) : null}

            {timelinePoints.map((point) => (
              <g key={point.snapshot.id}>
                <circle
                  cx={point.x}
                  cy={point.y}
                  r={timelineSnapshot?.id === point.snapshot.id ? 5 : 4}
                  className={styles.readinessTimelinePoint}
                  data-testid="broker-readiness-timeline-point"
                  onMouseEnter={() => onSelectTimelineSnapshot(point.snapshot.id)}
                />
              </g>
            ))}
          </svg>
        </div>

        <div className={styles.readinessTimelineBars}>
          {timelineSnapshots.map((snapshot) => {
            const counts = summarizeSnapshotCounts(snapshot);
            const total = Math.max(snapshot.total_count, 1);
            return (
              <button
                key={snapshot.id}
                type="button"
                className={`${styles.readinessTimelineBar} ${timelineSnapshot?.id === snapshot.id ? styles.readinessTimelineBarSelected : ""}`}
                data-testid="broker-readiness-timeline-bar"
                onClick={() => onSelectTimelineSnapshot(snapshot.id)}
              >
                <span
                  className={styles.readinessTimelineBarReady}
                  style={{ width: `${(counts.ready / total) * 100}%` }}
                />
                <span
                  className={styles.readinessTimelineBarAdvisory}
                  style={{ width: `${(counts.advisory / total) * 100}%` }}
                />
                <span
                  className={styles.readinessTimelineBarMissing}
                  style={{ width: `${(counts.missing / total) * 100}%` }}
                />
              </button>
            );
          })}
        </div>

        {timelineSnapshot !== null && (
          <div className={styles.readinessTimelineDetail} data-testid="broker-readiness-timeline-detail">
            <span className={styles.readinessTimelineDetailTitle}>{formatTimestamp(timelineSnapshot.captured_at)}</span>
            <span className={styles.readinessTimelineDetailText}>
              Ready: {summarizeSnapshotCounts(timelineSnapshot).ready} · Advisory: {summarizeSnapshotCounts(timelineSnapshot).advisory} · Missing: {summarizeSnapshotCounts(timelineSnapshot).missing}
            </span>
            <span className={styles.readinessTimelineDetailText}>
              Score: {timelineSnapshot.total_count > 0 ? `${Math.round((timelineSnapshot.ready_count / timelineSnapshot.total_count) * 100)}%` : "0%"}
            </span>
          </div>
        )}
      </div>
    </>
  );
}