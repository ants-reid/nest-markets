import type {
  BrokerOrderAuditEntry,
  NormalizedBrokerTradeEvent,
} from "../../lib/api/broker";

export type ChecklistItemStatus = "ready" | "missing" | "advisory";

export type ReadinessChecklistItem = {
  id: string;
  label: string;
  status: ChecklistItemStatus;
  detail: string;
};

export type ReadinessSnapshot = {
  id: string;
  captured_at: string;
  ready_count: number;
  total_count: number;
  summary_text: string;
  items: ReadinessChecklistItem[];
};

export type ProvenanceExportRecord = {
  event_fingerprint: string;
  external_trade_id: string | null;
  broker_order_id: string | null;
  symbol: string | null;
  side: string | null;
  quantity: number | null;
  fill_price: number | null;
  commission: number | null;
  net_amount: number | null;
  realized_pnl: number | null;
  trade_ts: string | null;
  source: string;
  account_id: string | null;
  broker_provider: string;
  created_at: string;
};

export type ReadinessBackupPack = {
  format: "mh-broker-readiness-backup-pack-v1";
  exported_at: string;
  metadata?: {
    account_id: string | null;
    broker_mode: string | null;
  };
  snapshots: ReadinessSnapshot[];
  current_readiness: {
    snapshot: ReadinessSnapshot;
  };
  provenance_export?: {
    exported_at: string;
    rows: ProvenanceExportRecord[];
  };
  audit_export?: {
    exported_at: string;
    entries: BrokerOrderAuditEntry[];
  };
};

export type BackupPackSummary = {
  exportedAt: string;
  snapshotCount: number;
  provenanceRowCount: number;
  auditRowCount: number;
  accountId: string | null;
  brokerMode: string | null;
  source: "export" | "import";
};

export type BackupPackDetailSection = "snapshots" | "provenance" | "audit";

export type CopyState = "idle" | "copied" | "error";

export type BackupPackViewModel = {
  snapshotHistory: ReadinessSnapshot[];
  currentSnapshot: ReadinessSnapshot | null;
  provenanceRows: ProvenanceExportRecord[];
  auditRows: BrokerOrderAuditEntry[];
  currentCounts: Record<ChecklistItemStatus, number>;
  snapshotAverageReady: number;
  provenanceSymbolCount: number;
  provenancePnlPresentCount: number;
  auditDryRunCount: number;
  auditSubmitCount: number;
  auditIssueCount: number;
  sectionMeta: string;
  reportMarkdown: string;
  sourceLabel: string;
};

export type ReadinessComparisonChange = {
  id: string;
  label: string;
  previousStatus: ChecklistItemStatus;
  currentStatus: ChecklistItemStatus;
  previousDetail: string;
  currentDetail: string;
  changeType: "improved" | "regressed";
};

export type TimelinePoint = {
  snapshot: ReadinessSnapshot;
  score: number;
  x: number;
  y: number;
};

export const MAX_READINESS_SNAPSHOTS = 8;

export const CHECKLIST_STATUS_SCORE: Record<ChecklistItemStatus, number> = {
  missing: 0,
  advisory: 1,
  ready: 2,
};

export function formatTimestamp(ts: string): string {
  const parsed = new Date(ts);
  if (Number.isNaN(parsed.getTime())) return ts;
  return parsed.toLocaleString("en-US", {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isChecklistItemStatus(value: unknown): value is ChecklistItemStatus {
  return value === "ready" || value === "missing" || value === "advisory";
}

function isReadinessChecklistItem(value: unknown): value is ReadinessChecklistItem {
  return isRecord(value)
    && typeof value.id === "string"
    && typeof value.label === "string"
    && isChecklistItemStatus(value.status)
    && typeof value.detail === "string";
}

function isReadinessSnapshot(value: unknown): value is ReadinessSnapshot {
  return isRecord(value)
    && typeof value.id === "string"
    && typeof value.captured_at === "string"
    && typeof value.ready_count === "number"
    && Number.isFinite(value.ready_count)
    && typeof value.total_count === "number"
    && Number.isFinite(value.total_count)
    && typeof value.summary_text === "string"
    && Array.isArray(value.items)
    && value.items.every((item) => isReadinessChecklistItem(item));
}

function isNullableNumber(value: unknown): value is number | null {
  return value === null || (typeof value === "number" && Number.isFinite(value));
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function isProvenanceExportRecord(value: unknown): value is ProvenanceExportRecord {
  return isRecord(value)
    && typeof value.event_fingerprint === "string"
    && isNullableString(value.external_trade_id)
    && isNullableString(value.broker_order_id)
    && isNullableString(value.symbol)
    && isNullableString(value.side)
    && isNullableNumber(value.quantity)
    && isNullableNumber(value.fill_price)
    && isNullableNumber(value.commission)
    && isNullableNumber(value.net_amount)
    && isNullableNumber(value.realized_pnl)
    && isNullableString(value.trade_ts)
    && typeof value.source === "string"
    && isNullableString(value.account_id)
    && typeof value.broker_provider === "string"
    && typeof value.created_at === "string";
}

function isBrokerOrderAuditIssue(value: unknown): value is { code?: string; message?: string } {
  return isRecord(value)
    && (value.code === undefined || typeof value.code === "string")
    && (value.message === undefined || typeof value.message === "string");
}

function isBrokerOrderAuditEntry(value: unknown): value is BrokerOrderAuditEntry {
  return isRecord(value)
    && typeof value.ts === "string"
    && typeof value.event === "string"
    && typeof value.action === "string"
    && typeof value.ticker === "string"
    && typeof value.side === "string"
    && isNullableNumber(value.quantity)
    && typeof value.status === "string"
    && isNullableString(value.broker_order_id)
    && isNullableString(value.reason)
    && typeof value.dry_run === "boolean"
    && Array.isArray(value.issues)
    && value.issues.every((issue) => isBrokerOrderAuditIssue(issue));
}

export function isReadinessBackupPack(value: unknown): value is ReadinessBackupPack {
  return isRecord(value)
    && value.format === "mh-broker-readiness-backup-pack-v1"
    && typeof value.exported_at === "string"
    && (value.metadata === undefined || (
      isRecord(value.metadata)
      && isNullableString(value.metadata.account_id)
      && isNullableString(value.metadata.broker_mode)
    ))
    && Array.isArray(value.snapshots)
    && value.snapshots.every((snapshot) => isReadinessSnapshot(snapshot))
    && isRecord(value.current_readiness)
    && isReadinessSnapshot(value.current_readiness.snapshot)
    && (value.provenance_export === undefined || (
      isRecord(value.provenance_export)
      && typeof value.provenance_export.exported_at === "string"
      && Array.isArray(value.provenance_export.rows)
      && value.provenance_export.rows.every((row) => isProvenanceExportRecord(row))
    ))
    && (value.audit_export === undefined || (
      isRecord(value.audit_export)
      && typeof value.audit_export.exported_at === "string"
      && Array.isArray(value.audit_export.entries)
      && value.audit_export.entries.every((entry) => isBrokerOrderAuditEntry(entry))
    ));
}

export function toProvenanceExportRecord(entry: NormalizedBrokerTradeEvent): ProvenanceExportRecord {
  return {
    event_fingerprint: entry.event_fingerprint,
    external_trade_id: entry.external_trade_id,
    broker_order_id: entry.broker_order_id,
    symbol: entry.symbol,
    side: entry.side,
    quantity: entry.quantity,
    fill_price: entry.fill_price,
    commission: entry.commission,
    net_amount: entry.net_amount,
    realized_pnl: entry.realized_pnl,
    trade_ts: entry.trade_ts,
    source: entry.source,
    account_id: entry.account_id,
    broker_provider: entry.broker_provider,
    created_at: entry.created_at,
  };
}

export function summarizeBackupPack(pack: ReadinessBackupPack, source: "export" | "import"): BackupPackSummary {
  return {
    exportedAt: pack.exported_at,
    snapshotCount: pack.snapshots.length,
    provenanceRowCount: pack.provenance_export?.rows.length ?? 0,
    auditRowCount: pack.audit_export?.entries.length ?? 0,
    accountId: pack.metadata?.account_id ?? null,
    brokerMode: pack.metadata?.broker_mode ?? null,
    source,
  };
}

export function backupPackSectionLabel(section: BackupPackDetailSection): string {
  if (section === "snapshots") return "Readiness snapshots";
  if (section === "provenance") return "Provenance rows";
  return "Audit rows";
}

export function buildBackupPackSectionPayload(pack: ReadinessBackupPack, section: BackupPackDetailSection): Record<string, unknown> {
  if (section === "snapshots") {
    return {
      format: pack.format,
      section,
      exported_at: pack.exported_at,
      metadata: pack.metadata ?? null,
      snapshots: pack.snapshots,
      current_readiness: pack.current_readiness,
    };
  }
  if (section === "provenance") {
    return {
      format: pack.format,
      section,
      exported_at: pack.provenance_export?.exported_at ?? pack.exported_at,
      metadata: pack.metadata ?? null,
      rows: pack.provenance_export?.rows ?? [],
    };
  }
  return {
    format: pack.format,
    section,
    exported_at: pack.audit_export?.exported_at ?? pack.exported_at,
    metadata: pack.metadata ?? null,
    entries: pack.audit_export?.entries ?? [],
  };
}

export function checklistStatusLabel(status: ChecklistItemStatus): string {
  if (status === "ready") return "Ready";
  if (status === "missing") return "Missing";
  return "Advisory";
}

export function summarizeSnapshotStatuses(snapshot: ReadinessSnapshot | null): Record<ChecklistItemStatus, number> {
  const counts: Record<ChecklistItemStatus, number> = {
    ready: 0,
    advisory: 0,
    missing: 0,
  };
  if (snapshot == null) {
    return counts;
  }
  for (const item of snapshot.items) {
    counts[item.status] += 1;
  }
  return counts;
}

function buildBackupPackReportMarkdown({
  pack,
  summary,
  currentSnapshot,
  currentCounts,
  snapshotCount,
  snapshotAverageReady,
  provenanceRowCount,
  provenanceSymbolCount,
  provenancePnlPresentCount,
  auditRowCount,
  auditDryRunCount,
  auditSubmitCount,
  auditIssueCount,
}: {
  pack: ReadinessBackupPack;
  summary: BackupPackSummary | null;
  currentSnapshot: ReadinessSnapshot | null;
  currentCounts: Record<ChecklistItemStatus, number>;
  snapshotCount: number;
  snapshotAverageReady: number;
  provenanceRowCount: number;
  provenanceSymbolCount: number;
  provenancePnlPresentCount: number;
  auditRowCount: number;
  auditDryRunCount: number;
  auditSubmitCount: number;
  auditIssueCount: number;
}): string {
  return [
    "# Backup Pack Human Review Report",
    "",
    `Generated: ${formatTimestamp(pack.exported_at)}`,
    `Account: ${pack.metadata?.account_id ?? "—"}`,
    `Mode: ${pack.metadata?.broker_mode ?? "—"}`,
    `Source: ${summary?.source === "export" ? "Last exported backup pack" : "Last imported backup pack"}`,
    "",
    "## Readiness Summary",
    `- Current baseline: ${currentSnapshot?.ready_count ?? 0}/${currentSnapshot?.total_count ?? 0} ready`,
    `- Ready: ${currentCounts.ready}`,
    `- Advisory: ${currentCounts.advisory}`,
    `- Missing: ${currentCounts.missing}`,
    "",
    "## Snapshots Summary",
    `- Saved snapshots in pack: ${snapshotCount}`,
    `- Average saved readiness score: ${snapshotAverageReady}%`,
    "",
    "## Provenance Summary",
    `- Provenance rows: ${provenanceRowCount}`,
    `- Symbols represented: ${provenanceSymbolCount}`,
    `- Rows with realized P&L present: ${provenancePnlPresentCount}`,
    "",
    "## Audit Summary",
    `- Audit rows: ${auditRowCount}`,
    `- Dry run rows: ${auditDryRunCount}`,
    `- Submit rows: ${auditSubmitCount}`,
    `- Rows with issues: ${auditIssueCount}`,
    "",
    "---",
    `Local-only review artifact · ${pack.format}`,
  ].join("\n");
}

export function summarizeSnapshotStatusesFallback(snapshot: ReadinessSnapshot): Record<ChecklistItemStatus, number> {
  if (snapshot.items.length > 0) {
    return summarizeSnapshotStatuses(snapshot);
  }
  const ready = Math.max(0, snapshot.ready_count);
  const advisory = Math.max(0, snapshot.total_count - ready);
  return {
    ready,
    advisory,
    missing: 0,
  };
}

export function buildBackupPackViewModel(
  pack: ReadinessBackupPack | null,
  summary: BackupPackSummary | null,
  section: BackupPackDetailSection,
): BackupPackViewModel {
  const snapshotHistory = pack?.snapshots ?? [];
  const currentSnapshot = pack?.current_readiness.snapshot ?? null;
  const provenanceRows = pack?.provenance_export?.rows ?? [];
  const auditRows = pack?.audit_export?.entries ?? [];
  const currentCounts = currentSnapshot != null
    ? summarizeSnapshotStatusesFallback(currentSnapshot)
    : { ready: 0, advisory: 0, missing: 0 };
  const snapshotAverageReady = snapshotHistory.length > 0
    ? Math.round(
        snapshotHistory.reduce((total, snapshot) => total + (snapshot.total_count > 0 ? (snapshot.ready_count / snapshot.total_count) * 100 : 0), 0)
          / snapshotHistory.length,
      )
    : 0;
  const provenanceSymbolCount = new Set(
    provenanceRows.map((row) => row.symbol).filter((symbol): symbol is string => typeof symbol === "string" && symbol.length > 0),
  ).size;
  const provenancePnlPresentCount = provenanceRows.filter((row) => row.realized_pnl != null).length;
  const auditDryRunCount = auditRows.filter((entry) => entry.dry_run).length;
  const auditSubmitCount = auditRows.filter((entry) => !entry.dry_run).length;
  const auditIssueCount = auditRows.filter((entry) => entry.issues.length > 0).length;

  const sectionMeta = (() => {
    if (pack == null) {
      return "";
    }
    if (section === "snapshots") {
      return `${snapshotHistory.length} saved snapshot${snapshotHistory.length === 1 ? "" : "s"} plus current readiness baseline.`;
    }
    if (section === "provenance") {
      return `${provenanceRows.length} provenance row${provenanceRows.length === 1 ? "" : "s"} included in this pack.`;
    }
    return `${auditRows.length} audit row${auditRows.length === 1 ? "" : "s"} included in this pack.`;
  })();

  return {
    snapshotHistory,
    currentSnapshot,
    provenanceRows,
    auditRows,
    currentCounts,
    snapshotAverageReady,
    provenanceSymbolCount,
    provenancePnlPresentCount,
    auditDryRunCount,
    auditSubmitCount,
    auditIssueCount,
    sectionMeta,
    reportMarkdown: pack == null
      ? ""
      : buildBackupPackReportMarkdown({
          pack,
          summary,
          currentSnapshot,
          currentCounts,
          snapshotCount: snapshotHistory.length,
          snapshotAverageReady,
          provenanceRowCount: provenanceRows.length,
          provenanceSymbolCount,
          provenancePnlPresentCount,
          auditRowCount: auditRows.length,
          auditDryRunCount,
          auditSubmitCount,
          auditIssueCount,
        }),
    sourceLabel: summary?.source === "export" ? "Last exported backup pack" : "Last imported backup pack",
  };
}

export function parseImportedReadinessSnapshots(payload: unknown): { snapshots: ReadinessSnapshot[]; source: "history-json" | "backup-pack" } | null {
  if (Array.isArray(payload)) {
    return payload.every((entry) => isReadinessSnapshot(entry)) ? { snapshots: payload, source: "history-json" } : null;
  }
  if (isRecord(payload)) {
    if (payload.format === "mh-broker-readiness-backup-pack-v1") {
      if (!isReadinessBackupPack(payload)) {
        return null;
      }
      return {
        snapshots: [...payload.snapshots, payload.current_readiness.snapshot],
        source: "backup-pack",
      };
    }
    if (Array.isArray(payload.snapshots)) {
      return payload.snapshots.every((entry) => isReadinessSnapshot(entry)) ? { snapshots: payload.snapshots, source: "history-json" } : null;
    }
  }
  return null;
}

function snapshotSortKey(snapshot: ReadinessSnapshot): number {
  const parsed = new Date(snapshot.captured_at).getTime();
  return Number.isNaN(parsed) ? 0 : parsed;
}

export function mergeReadinessSnapshots(existing: ReadinessSnapshot[], imported: ReadinessSnapshot[]): ReadinessSnapshot[] {
  const seenIds = new Set<string>();
  const seenTimestamps = new Set<string>();
  return [...existing, ...imported]
    .sort((left, right) => snapshotSortKey(right) - snapshotSortKey(left))
    .filter((snapshot) => {
      if (seenIds.has(snapshot.id) || seenTimestamps.has(snapshot.captured_at)) {
        return false;
      }
      seenIds.add(snapshot.id);
      seenTimestamps.add(snapshot.captured_at);
      return true;
    })
    .slice(0, MAX_READINESS_SNAPSHOTS);
}