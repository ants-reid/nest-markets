"use client";

import { useEffect, useRef, useState, type ChangeEvent } from "react";
import type {
  BrokerAccountInfo,
  BrokerDailyPnl,
  BrokerHealth,
  BrokerOrderAuditEntry,
  BrokerOrderDryRunResult,
  BrokerPosition,
  BrokerTradeEventAuditTrail,
  BrokerTradingControl,
} from "../../lib/api/broker";
import styles from "../../styles/pages/broker.module.css";
import {
  BackupPackDetailViewer,
  BackupPackSummaryPanel,
  ReadinessChecklistItemsList,
  ReadinessSavedHistorySection,
} from "./review-section-components";
import {
  CHECKLIST_STATUS_SCORE,
  MAX_READINESS_SNAPSHOTS,
  backupPackSectionLabel,
  buildBackupPackSectionPayload,
  buildBackupPackViewModel,
  checklistStatusLabel,
  formatTimestamp,
  isReadinessBackupPack,
  mergeReadinessSnapshots,
  parseImportedReadinessSnapshots,
  summarizeBackupPack,
  summarizeSnapshotStatuses,
  summarizeSnapshotStatusesFallback,
  toProvenanceExportRecord,
  type BackupPackDetailSection,
  type BackupPackSummary,
  type ChecklistItemStatus,
  type CopyState,
  type ReadinessBackupPack,
  type ReadinessChecklistItem,
  type ReadinessComparisonChange,
  type ReadinessSnapshot,
} from "./review-helpers";

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

const READINESS_HISTORY_STORAGE_KEY = "mh-broker-readiness-history";

function checklistStatusClass(status: ChecklistItemStatus): string {
  if (status === "ready") return styles.readinessItemReady;
  if (status === "missing") return styles.readinessItemMissing;
  return styles.readinessItemAdvisory;
}

function buildReadinessChecklistItems({
  state,
  health,
  control,
  dailyPnl,
  dryRun,
  formatControlValue,
}: {
  state: PageState;
  health: HealthState;
  control: ControlState;
  dailyPnl: BrokerDailyPnl | null;
  dryRun: BrokerOrderDryRunResult | null;
  formatControlValue: (value: string) => string;
}): ReadinessChecklistItem[] {
  return [
    {
      id: "portfolio-snapshot",
      label: "Portfolio snapshot loaded",
      status: state.status === "ready" ? "ready" : state.status === "error" ? "missing" : "advisory",
      detail:
        state.status === "ready"
          ? `${state.positions.length} open position${state.positions.length === 1 ? "" : "s"} loaded.`
          : state.status === "error"
            ? "Broker account/positions data failed to load."
            : "Broker account and positions are still loading.",
    },
    {
      id: "paper-mode",
      label: "Paper broker mode confirmed",
      status:
        health.status === "ready"
          ? health.data.status === "paper_ready" && health.data.account_is_paper && health.data.broker_mode.mode === "paper"
            ? "ready"
            : "missing"
          : health.status === "error"
            ? "missing"
            : "advisory",
      detail:
        health.status === "ready"
          ? `Account ${health.data.account_id} checked against broker paper-mode health.`
          : health.status === "error"
            ? "Broker health is unavailable."
            : "Waiting for broker health.",
    },
    {
      id: "gateway",
      label: "Gateway reachable",
      status:
        health.status === "ready"
          ? health.data.gateway_reachable
            ? "ready"
            : "missing"
          : health.status === "error"
            ? "missing"
            : "advisory",
      detail:
        health.status === "ready"
          ? `${health.data.gateway_url}`
          : health.status === "error"
            ? "Gateway health check failed."
            : "Waiting for gateway check.",
    },
    {
      id: "manual-paper-submit",
      label: "Manual paper submission available",
      status:
        control.status === "ready"
          ? control.data.trading_mode === "paper" && control.data.execution_control === "manual" && control.data.paper_order_submission_allowed
            ? "ready"
            : "missing"
          : control.status === "error"
            ? "missing"
            : "advisory",
      detail:
        control.status === "ready"
          ? `${formatControlValue(control.data.trading_mode)} mode · ${formatControlValue(control.data.execution_control)} control.`
          : control.status === "error"
            ? "Trading control is unavailable."
            : "Waiting for trading control.",
    },
    {
      id: "live-blocked",
      label: "Live submission remains blocked",
      status:
        control.status === "ready"
          ? !control.data.live_order_submission_allowed
            ? "ready"
            : "missing"
          : control.status === "error"
            ? "missing"
            : "advisory",
      detail:
        control.status === "ready"
          ? control.data.live_order_submission_allowed
            ? "Live submission is enabled."
            : "Live order submission blocked."
          : control.status === "error"
            ? "Unable to confirm live submission guard."
            : "Waiting for trading control.",
    },
    {
      id: "auto-locked",
      label: "Auto trading remains locked",
      status:
        control.status === "ready"
          ? !control.data.auto_trading_allowed
            ? "ready"
            : "missing"
          : control.status === "error"
            ? "missing"
            : "advisory",
      detail:
        control.status === "ready"
          ? control.data.auto_trading_allowed
            ? "Auto trading is enabled."
            : "Auto trading locked."
          : control.status === "error"
            ? "Unable to confirm auto trading lock."
            : "Waiting for trading control.",
    },
    {
      id: "daily-pnl-context",
      label: "Daily P&L context available",
      status:
        dailyPnl === null
          ? "missing"
          : dailyPnl.snapshot_count > 0
            ? "ready"
            : "advisory",
      detail:
        dailyPnl === null
          ? "Daily P&L context is unavailable."
          : dailyPnl.snapshot_count > 0
            ? `${dailyPnl.snapshot_count} snapshot${dailyPnl.snapshot_count === 1 ? "" : "s"} loaded for today.`
            : dailyPnl.note ?? "No daily P&L snapshots available yet.",
    },
    {
      id: "preflight-context",
      label: "Preflight advisory reviewed",
      status:
        dryRun === null
          ? "advisory"
          : dryRun.preflight_context !== null || (dryRun.warnings?.length ?? 0) > 0 || dryRun.status === "ready"
            ? "ready"
            : "advisory",
      detail:
        dryRun === null
          ? "Run a dry run to populate advisory preflight context."
          : `Dry run status: ${dryRun.status.toUpperCase()}.`,
    },
  ];
}

export function BrokerReadinessChecklistPanel({
  state,
  health,
  control,
  dailyPnl,
  dryRun,
  provenance,
  audit,
  formatControlValue,
  downloadTextFile,
  copyTextToClipboard,
}: {
  state: PageState;
  health: HealthState;
  control: ControlState;
  dailyPnl: BrokerDailyPnl | null;
  dryRun: BrokerOrderDryRunResult | null;
  provenance: ProvenanceState;
  audit: AuditState;
  formatControlValue: (value: string) => string;
  downloadTextFile: (content: string, filename: string, mimeType: string) => void;
  copyTextToClipboard: (text: string, setState: (next: CopyState) => void) => Promise<void>;
}) {
  const [copyState, setCopyState] = useState<CopyState>("idle");
  const [historyCopyState, setHistoryCopyState] = useState<CopyState>("idle");
  const [historyImportState, setHistoryImportState] = useState<{ status: "idle" | "success" | "error"; message: string }>({
    status: "idle",
    message: "",
  });
  const [backupPackSummary, setBackupPackSummary] = useState<BackupPackSummary | null>(null);
  const [backupPackDetail, setBackupPackDetail] = useState<ReadinessBackupPack | null>(null);
  const [backupPackDetailSection, setBackupPackDetailSection] = useState<BackupPackDetailSection>("snapshots");
  const [backupPackDetailCopyState, setBackupPackDetailCopyState] = useState<CopyState>("idle");
  const [backupPackReportCopyState, setBackupPackReportCopyState] = useState<CopyState>("idle");
  const [history, setHistory] = useState<ReadinessSnapshot[]>([]);
  const [selectedSnapshotId, setSelectedSnapshotId] = useState<string | null>(null);
  const [timelineSnapshotId, setTimelineSnapshotId] = useState<string | null>(null);
  const [confirmClearHistory, setConfirmClearHistory] = useState(false);
  const importInputRef = useRef<HTMLInputElement | null>(null);
  const items = buildReadinessChecklistItems({ state, health, control, dailyPnl, dryRun, formatControlValue });
  const readyCount = items.filter((item) => item.status === "ready").length;

  const summaryText = [
    `Broker readiness summary: ${readyCount}/${items.length} ready`,
    ...items.map((item) => `${checklistStatusLabel(item.status).toUpperCase()} - ${item.label}: ${item.detail}`),
  ].join("\n");
  const currentSnapshot: ReadinessSnapshot = {
    id: `current-${Date.now()}`,
    captured_at: new Date().toISOString(),
    ready_count: readyCount,
    total_count: items.length,
    summary_text: summaryText,
    items,
  };

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    try {
      const raw = window.localStorage.getItem(READINESS_HISTORY_STORAGE_KEY);
      if (!raw) {
        setHistory([]);
        return;
      }
      const parsed = JSON.parse(raw) as ReadinessSnapshot[];
      const nextHistory = Array.isArray(parsed) ? parsed : [];
      setHistory(nextHistory);
      setSelectedSnapshotId(nextHistory[0]?.id ?? null);
      setTimelineSnapshotId(nextHistory[0]?.id ?? null);
    } catch {
      setHistory([]);
      setSelectedSnapshotId(null);
      setTimelineSnapshotId(null);
    }
  }, []);

  function persistHistory(nextHistory: ReadinessSnapshot[]) {
    setHistory(nextHistory);
    setSelectedSnapshotId((current) => {
      if (nextHistory.length === 0) return null;
      if (current && nextHistory.some((snapshot) => snapshot.id === current)) return current;
      return nextHistory[0].id;
    });
    setTimelineSnapshotId((current) => {
      if (nextHistory.length === 0) return null;
      if (current && nextHistory.some((snapshot) => snapshot.id === current)) return current;
      return nextHistory[0].id;
    });
    if (typeof window === "undefined") {
      return;
    }
    try {
      window.localStorage.setItem(READINESS_HISTORY_STORAGE_KEY, JSON.stringify(nextHistory));
    } catch {
      // Local-only persistence is best effort.
    }
  }

  async function copySummary() {
    await copyTextToClipboard(summaryText, setCopyState);
  }

  function exportChecklistJson() {
    const payload = {
      exported_at: new Date().toISOString(),
      ready_count: readyCount,
      total_count: items.length,
      items,
    };
    downloadTextFile(
      JSON.stringify(payload, null, 2),
      `broker-readiness-${Date.now()}.json`,
      "application/json;charset=utf-8",
    );
  }

  function printSummary() {
    window.print();
  }

  function saveSnapshot() {
    const snapshot: ReadinessSnapshot = {
      id: `${Date.now()}`,
      captured_at: new Date().toISOString(),
      ready_count: readyCount,
      total_count: items.length,
      summary_text: summaryText,
      items,
    };
    persistHistory([snapshot, ...history].slice(0, MAX_READINESS_SNAPSHOTS));
    setConfirmClearHistory(false);
  }

  const selectedSnapshot = history.find((snapshot) => snapshot.id === selectedSnapshotId) ?? history[0] ?? null;
  const latestSnapshot = history[0] ?? null;
  const compareSnapshot = selectedSnapshot && latestSnapshot && selectedSnapshot.id !== latestSnapshot.id ? selectedSnapshot : null;
  const latestCounts = summarizeSnapshotStatuses(latestSnapshot);
  const compareCounts = summarizeSnapshotStatuses(compareSnapshot);
  const changedComparisonItems: ReadinessComparisonChange[] = latestSnapshot && compareSnapshot
    ? latestSnapshot.items
        .map((latestItem) => {
          const previousItem = compareSnapshot.items.find((item) => item.id === latestItem.id);
          if (!previousItem || previousItem.status === latestItem.status) {
            return null;
          }
          const scoreDelta = CHECKLIST_STATUS_SCORE[latestItem.status] - CHECKLIST_STATUS_SCORE[previousItem.status];
          const changeType: ReadinessComparisonChange["changeType"] = scoreDelta > 0 ? "improved" : "regressed";
          return {
            id: latestItem.id,
            label: latestItem.label,
            previousStatus: previousItem.status,
            currentStatus: latestItem.status,
            previousDetail: previousItem.detail,
            currentDetail: latestItem.detail,
            changeType,
          };
        })
        .filter((item): item is NonNullable<typeof item> => item !== null)
    : [];

  async function copySelectedSnapshotSummary() {
    if (selectedSnapshot == null) {
      return;
    }
    await copyTextToClipboard(selectedSnapshot.summary_text, setHistoryCopyState);
  }

  function exportHistoryJson() {
    const payload = {
      exported_at: new Date().toISOString(),
      snapshot_count: history.length,
      snapshots: history,
    };
    downloadTextFile(
      JSON.stringify(payload, null, 2),
      `broker-readiness-history-${Date.now()}.json`,
      "application/json;charset=utf-8",
    );
  }

  function exportHistoryCsv() {
    const headers = ["id", "captured_at", "ready_count", "total_count", "summary_text"];
    const lines = [
      headers.join(","),
      ...history.map((snapshot) => [
        snapshot.id,
        snapshot.captured_at,
        String(snapshot.ready_count),
        String(snapshot.total_count),
        snapshot.summary_text.replace(/\n/g, " | "),
      ].map((value) => `"${value.replace(/"/g, '""')}"`).join(",")),
    ];
    downloadTextFile(
      lines.join("\n"),
      `broker-readiness-history-${Date.now()}.csv`,
      "text/csv;charset=utf-8",
    );
  }

  function showBackupPack(pack: ReadinessBackupPack, source: "export" | "import") {
    setBackupPackSummary(summarizeBackupPack(pack, source));
    setBackupPackDetail(pack);
    setBackupPackDetailSection("snapshots");
    setBackupPackDetailCopyState("idle");
    setBackupPackReportCopyState("idle");
  }

  function exportBackupPack() {
    const exportedAt = new Date().toISOString();
    const backupPack: ReadinessBackupPack = {
      format: "mh-broker-readiness-backup-pack-v1",
      exported_at: exportedAt,
      metadata: {
        account_id: health.status === "ready" ? health.data.account_id : provenance.status === "ready" ? provenance.data.account_id : null,
        broker_mode: health.status === "ready" ? health.data.broker_mode.mode : provenance.status === "ready" ? provenance.data.broker_mode?.mode ?? null : null,
      },
      snapshots: history,
      current_readiness: {
        snapshot: {
          ...currentSnapshot,
          id: `current-${exportedAt}`,
          captured_at: exportedAt,
        },
      },
      provenance_export: provenance.status === "ready"
        ? {
            exported_at: exportedAt,
            rows: provenance.data.entries.map((entry) => toProvenanceExportRecord(entry)),
          }
        : undefined,
      audit_export: audit.status === "ready"
        ? {
            exported_at: exportedAt,
            entries: audit.entries,
          }
        : undefined,
    };
    downloadTextFile(
      JSON.stringify(backupPack, null, 2),
      `broker-readiness-backup-pack-${Date.now()}.json`,
      "application/json;charset=utf-8",
    );
    showBackupPack(backupPack, "export");
  }

  function clearHistory() {
    persistHistory([]);
    setConfirmClearHistory(false);
    setHistoryCopyState("idle");
  }

  function openImportPicker() {
    importInputRef.current?.click();
  }

  async function importHistory(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    event.target.value = "";
    if (file == null) {
      return;
    }
    try {
      const rawText = await file.text();
      const payload = JSON.parse(rawText) as unknown;
      const importedPayload = parseImportedReadinessSnapshots(payload);
      if (importedPayload == null) {
        setHistoryImportState({
          status: "error",
          message: "Import failed. Snapshot file format is invalid.",
        });
        return;
      }
      if (isReadinessBackupPack(payload)) {
        showBackupPack(payload, "import");
      }
      const mergedHistory = mergeReadinessSnapshots(history, importedPayload.snapshots);
      const addedCount = Math.max(0, mergedHistory.length - history.length);
      persistHistory(mergedHistory);
      setConfirmClearHistory(false);
      setHistoryImportState({
        status: "success",
        message: addedCount > 0
          ? importedPayload.source === "backup-pack"
            ? `Imported ${addedCount} readiness snapshot${addedCount === 1 ? "" : "s"} from backup pack.`
            : `Imported ${addedCount} readiness snapshot${addedCount === 1 ? "" : "s"}.`
          : importedPayload.source === "backup-pack"
            ? "Import complete. No new readiness snapshots were added from backup pack."
            : "Import complete. No new readiness snapshots were added.",
      });
    } catch {
      setHistoryImportState({
        status: "error",
        message: "Import failed. Snapshot file must be valid JSON.",
      });
    }
  }

  const timelineSnapshots = [...history].reverse();
  const timelineChartWidth = 560;
  const timelineChartHeight = 132;
  const timelinePadX = 18;
  const timelinePadY = 16;
  const timelineSnapshot = history.find((snapshot) => snapshot.id === timelineSnapshotId) ?? history[0] ?? null;

  const timelinePoints = timelineSnapshots.map((snapshot, index) => {
    const score = snapshot.total_count > 0 ? (snapshot.ready_count / snapshot.total_count) * 100 : 0;
    const x =
      timelineSnapshots.length <= 1
        ? timelineChartWidth / 2
        : timelinePadX + (index * (timelineChartWidth - timelinePadX * 2)) / (timelineSnapshots.length - 1);
    const y = timelinePadY + ((100 - score) / 100) * (timelineChartHeight - timelinePadY * 2);
    return { snapshot, score, x, y };
  });
  const timelinePath = timelinePoints.map((point) => `${point.x},${point.y}`).join(" ");
  const backupPackView = buildBackupPackViewModel(backupPackDetail, backupPackSummary, backupPackDetailSection);

  async function copySelectedBackupPackSection() {
    if (backupPackDetail == null) {
      return;
    }
    await copyTextToClipboard(
      JSON.stringify(buildBackupPackSectionPayload(backupPackDetail, backupPackDetailSection), null, 2),
      setBackupPackDetailCopyState,
    );
  }

  function exportSelectedBackupPackSection() {
    if (backupPackDetail == null) {
      return;
    }
    downloadTextFile(
      JSON.stringify(buildBackupPackSectionPayload(backupPackDetail, backupPackDetailSection), null, 2),
      `broker-readiness-backup-pack-${backupPackDetailSection}-${Date.now()}.json`,
      "application/json;charset=utf-8",
    );
  }

  function printBackupPackReport() {
    window.print();
  }

  async function copyBackupPackReport() {
    if (!backupPackView.reportMarkdown) {
      return;
    }
    await copyTextToClipboard(backupPackView.reportMarkdown, setBackupPackReportCopyState);
  }

  function exportBackupPackReport(extension: "txt" | "md", mimeType: string) {
    if (!backupPackView.reportMarkdown) {
      return;
    }
    downloadTextFile(
      backupPackView.reportMarkdown,
      `broker-readiness-backup-pack-report-${Date.now()}.${extension}`,
      mimeType,
    );
  }

  return (
    <section className={styles.readinessPanel} data-testid="broker-readiness-panel">
      <div className={styles.readinessHeader}>
        <div>
          <h3 className={styles.sectionTitle}>Broker Readiness Checklist</h3>
          <p className={styles.readinessSummary}>Read-only status derived from current broker, control, P&amp;L, and preflight state.</p>
        </div>
        <div className={styles.readinessHeaderActions}>
          <span className={styles.readinessCount} data-testid="broker-readiness-count">
            {readyCount}/{items.length} ready
          </span>
          <button
            type="button"
            className={`${styles.secondaryButton} ${styles.readinessActionButton}`}
            onClick={saveSnapshot}
            data-testid="broker-readiness-save-snapshot"
          >
            Save Snapshot
          </button>
          <button
            type="button"
            className={`${styles.secondaryButton} ${styles.readinessActionButton}`}
            onClick={copySummary}
            data-testid="broker-readiness-copy-summary"
          >
            Copy Summary
          </button>
          <button
            type="button"
            className={`${styles.secondaryButton} ${styles.readinessActionButton}`}
            onClick={exportChecklistJson}
            data-testid="broker-readiness-export-json"
          >
            Export JSON
          </button>
          <button
            type="button"
            className={`${styles.secondaryButton} ${styles.readinessActionButton} ${styles.readinessPrintButton}`}
            onClick={printSummary}
            data-testid="broker-readiness-print-summary"
          >
            Print Summary
          </button>
        </div>
      </div>
      {copyState === "copied" && (
        <div className={styles.readinessCopyState} data-testid="broker-readiness-copy-state">Copied readiness summary.</div>
      )}
      {copyState === "error" && (
        <div className={styles.readinessCopyStateError} data-testid="broker-readiness-copy-state">Clipboard unavailable.</div>
      )}
      <ReadinessChecklistItemsList
        items={items}
        getStatusClassName={checklistStatusClass}
        getStatusLabel={checklistStatusLabel}
      />
      <div className={styles.readinessHistoryPanel} data-testid="broker-readiness-history-panel">
        <div className={styles.readinessHistoryHeader}>
          <span className={styles.readinessHistoryTitle}>Latest Readiness Snapshots</span>
          <div className={styles.readinessHistoryActions}>
            <span className={styles.readinessHistoryMeta} data-testid="broker-readiness-history-count">
              {history.length} saved
            </span>
            <button
              type="button"
              className={`${styles.secondaryButton} ${styles.readinessActionButton}`}
              onClick={exportHistoryJson}
              data-testid="broker-readiness-history-export-json"
              disabled={history.length === 0}
            >
              Export JSON
            </button>
            <button
              type="button"
              className={`${styles.secondaryButton} ${styles.readinessActionButton}`}
              onClick={exportBackupPack}
              data-testid="broker-readiness-history-export-backup-pack"
            >
              Export Backup Pack
            </button>
            <button
              type="button"
              className={`${styles.secondaryButton} ${styles.readinessActionButton}`}
              onClick={openImportPicker}
              data-testid="broker-readiness-history-import-json"
            >
              Import JSON
            </button>
            <button
              type="button"
              className={`${styles.secondaryButton} ${styles.readinessActionButton}`}
              onClick={exportHistoryCsv}
              data-testid="broker-readiness-history-export-csv"
              disabled={history.length === 0}
            >
              Export CSV
            </button>
            <button
              type="button"
              className={`${styles.secondaryButton} ${styles.readinessActionButton}`}
              onClick={copySelectedSnapshotSummary}
              data-testid="broker-readiness-history-copy-selected"
              disabled={selectedSnapshot == null}
            >
              Copy Selected
            </button>
            {!confirmClearHistory ? (
              <button
                type="button"
                className={`${styles.secondaryButton} ${styles.readinessActionButton}`}
                onClick={() => setConfirmClearHistory(true)}
                data-testid="broker-readiness-history-clear"
                disabled={history.length === 0}
              >
                Clear History
              </button>
            ) : (
              <div className={styles.readinessHistoryConfirm} data-testid="broker-readiness-history-clear-confirm">
                <span className={styles.readinessHistoryConfirmText}>Clear all saved local snapshots?</span>
                <button
                  type="button"
                  className={styles.confirmBtn}
                  onClick={clearHistory}
                  data-testid="broker-readiness-history-clear-confirm-yes"
                >
                  Confirm
                </button>
                <button
                  type="button"
                  className={styles.cancelBtn}
                  onClick={() => setConfirmClearHistory(false)}
                  data-testid="broker-readiness-history-clear-confirm-no"
                >
                  Cancel
                </button>
              </div>
            )}
          </div>
        </div>
        <input
          ref={importInputRef}
          type="file"
          accept="application/json,.json"
          className={styles.readinessHistoryFileInput}
          data-testid="broker-readiness-history-import-input"
          onChange={importHistory}
        />
        {historyCopyState === "copied" && (
          <div className={styles.readinessCopyState} data-testid="broker-readiness-history-copy-state">Copied selected readiness snapshot.</div>
        )}
        {historyCopyState === "error" && (
          <div className={styles.readinessCopyStateError} data-testid="broker-readiness-history-copy-state">Clipboard unavailable.</div>
        )}
        {historyImportState.status === "success" && (
          <div className={styles.readinessCopyState} data-testid="broker-readiness-history-import-state">{historyImportState.message}</div>
        )}
        {historyImportState.status === "error" && (
          <div className={styles.readinessCopyStateError} data-testid="broker-readiness-history-import-state">{historyImportState.message}</div>
        )}
        {backupPackSummary !== null && (
          <BackupPackSummaryPanel
            summary={backupPackSummary}
            formatTimestamp={formatTimestamp}
          />
        )}
        {backupPackDetail !== null && (
          <BackupPackDetailViewer
            detail={backupPackDetail}
            section={backupPackDetailSection}
            view={backupPackView}
            detailCopyState={backupPackDetailCopyState}
            reportCopyState={backupPackReportCopyState}
            onSelectSection={(section) => {
              setBackupPackDetailSection(section);
              setBackupPackDetailCopyState("idle");
            }}
            onCopyReport={copyBackupPackReport}
            onExportReport={exportBackupPackReport}
            onCopySection={copySelectedBackupPackSection}
            onExportSection={exportSelectedBackupPackSection}
            onPrintReport={printBackupPackReport}
            formatTimestamp={formatTimestamp}
            getSectionLabel={backupPackSectionLabel}
          />
        )}
        <ReadinessSavedHistorySection
          history={history}
          selectedSnapshot={selectedSnapshot}
          onSelectSnapshot={setSelectedSnapshotId}
          latestSnapshot={latestSnapshot}
          compareSnapshot={compareSnapshot}
          compareCounts={compareCounts}
          latestCounts={latestCounts}
          changedComparisonItems={changedComparisonItems}
          timelineSnapshots={timelineSnapshots}
          timelineSnapshot={timelineSnapshot}
          timelinePoints={timelinePoints}
          timelinePath={timelinePath}
          timelineChartWidth={timelineChartWidth}
          timelineChartHeight={timelineChartHeight}
          timelinePadX={timelinePadX}
          timelinePadY={timelinePadY}
          onSelectTimelineSnapshot={setTimelineSnapshotId}
          formatTimestamp={formatTimestamp}
          getStatusLabel={checklistStatusLabel}
          summarizeSnapshotCounts={summarizeSnapshotStatusesFallback}
        />
      </div>
    </section>
  );
}