"use client";

import { useState } from "react";
import type {
  BrokerTradeEventAuditTrail,
  NormalizedBrokerTradeEvent,
} from "../../lib/api/broker";
import styles from "../../styles/pages/broker.module.css";
import { toProvenanceExportRecord, type CopyState } from "./review-helpers";

type ProvenanceState =
  | { status: "loading" }
  | { status: "ready"; data: BrokerTradeEventAuditTrail }
  | { status: "error" };

export function BrokerTradeProvenancePanel({
  provenance,
  formatTimestamp,
  formatMoney,
  getPnlClassName,
  getSideBadgeClass,
  downloadTextFile,
  copyTextToClipboard,
}: {
  provenance: ProvenanceState;
  formatTimestamp: (value: string) => string;
  formatMoney: (value: number, currency?: string) => string;
  getPnlClassName: (value: number | null) => string;
  getSideBadgeClass: (side: string | null) => string;
  downloadTextFile: (content: string, filename: string, mimeType: string) => void;
  copyTextToClipboard: (text: string, setState: (next: CopyState) => void) => Promise<void>;
}) {
  const [filterSymbol, setFilterSymbol] = useState("");
  const [filterSource, setFilterSource] = useState("");
  const [filterAccount, setFilterAccount] = useState("");
  const [filterPnlOnly, setFilterPnlOnly] = useState(false);
  const [selectedEntry, setSelectedEntry] = useState<NormalizedBrokerTradeEvent | null>(null);
  const [copyState, setCopyState] = useState<CopyState>("idle");

  const entries: NormalizedBrokerTradeEvent[] =
    provenance.status === "ready" ? provenance.data.entries : [];

  const filtered = entries.filter((entry) => {
    if (filterSymbol && !(entry.symbol ?? "").toLowerCase().includes(filterSymbol.toLowerCase())) return false;
    if (filterSource && !(entry.source ?? "").toLowerCase().includes(filterSource.toLowerCase())) return false;
    if (filterAccount && !(entry.account_id ?? "").toLowerCase().includes(filterAccount.toLowerCase())) return false;
    if (filterPnlOnly && entry.realized_pnl == null) return false;
    return true;
  });

  function exportFilteredAsJson() {
    const rows = filtered.map((entry) => toProvenanceExportRecord(entry));
    const payload = {
      exported_at: new Date().toISOString(),
      filters: {
        symbol: filterSymbol,
        source: filterSource,
        account: filterAccount,
        realized_pnl_present_only: filterPnlOnly,
      },
      rows,
    };
    downloadTextFile(
      JSON.stringify(payload, null, 2),
      `broker-trade-provenance-${Date.now()}.json`,
      "application/json;charset=utf-8",
    );
  }

  function exportFilteredAsCsv() {
    const headers = [
      "event_fingerprint",
      "external_trade_id",
      "broker_order_id",
      "symbol",
      "side",
      "quantity",
      "fill_price",
      "commission",
      "net_amount",
      "realized_pnl",
      "trade_ts",
      "source",
      "account_id",
      "broker_provider",
      "created_at",
    ];

    const csvLines = [
      headers.join(","),
      ...filtered.map((entry) => {
        const record = toProvenanceExportRecord(entry);
        return headers
          .map((header) => {
            const value = record[header as keyof typeof record];
            const text = value == null ? "" : String(value);
            return `"${text.replace(/"/g, '""')}"`;
          })
          .join(",");
      }),
    ];

    downloadTextFile(
      csvLines.join("\n"),
      `broker-trade-provenance-${Date.now()}.csv`,
      "text/csv;charset=utf-8",
    );
  }

  async function copySelectedDetail() {
    if (selectedEntry == null) {
      return;
    }
    await copyTextToClipboard(JSON.stringify(toProvenanceExportRecord(selectedEntry), null, 2), setCopyState);
  }

  const reconciliationNotes = (() => {
    if (selectedEntry == null) {
      return [] as string[];
    }
    const notes: string[] = [];
    if (selectedEntry.external_trade_id || selectedEntry.broker_order_id) {
      notes.push("Broker/external identifiers present for reconciliation.");
    }
    if (selectedEntry.realized_pnl == null) {
      notes.push("Realized P&L is missing from this event; compare against broker statement exports.");
    }
    if (selectedEntry.commission == null) {
      notes.push("Commission is missing from this event.");
    }
    if (selectedEntry.net_amount == null) {
      notes.push("Net amount is missing from this event.");
    }
    if (notes.length === 0) {
      notes.push("No reconciliation gaps detected in currently available event fields.");
    }
    return notes;
  })();

  return (
    <section className={styles.provenancePanel} data-testid="broker-trade-provenance-panel">
      <div className={styles.auditHeaderRow}>
        <h2 className={styles.sectionTitle}>Normalized Trade Event Provenance</h2>
        {provenance.status === "ready" && (
          <span className={styles.auditCount} data-testid="broker-trade-provenance-count">
            {provenance.data.returned} events
          </span>
        )}
      </div>

      {provenance.status === "loading" && (
        <div className={styles.auditEmpty}>Loading normalized trade events...</div>
      )}

      {provenance.status === "error" && (
        <div className={styles.auditEmpty}>Normalized trade provenance unavailable.</div>
      )}

      {provenance.status === "ready" && entries.length === 0 && (
        <div className={styles.auditEmpty}>No normalized trade events yet.</div>
      )}

      {provenance.status === "ready" && entries.length > 0 && (
        <>
          <p className={styles.provenanceMeta} data-testid="broker-trade-provenance-meta">
            Account: {provenance.data.account_id ?? "—"} · Mode: {provenance.data.broker_mode?.mode ?? "unknown"}
          </p>

          <div className={styles.provenanceFilterBar} data-testid="broker-trade-provenance-filters">
            <input
              className={styles.provenanceFilterInput}
              type="text"
              placeholder="Symbol"
              value={filterSymbol}
              onChange={(e) => setFilterSymbol(e.target.value)}
              aria-label="Filter by symbol"
              data-testid="broker-trade-provenance-filter-symbol"
            />
            <input
              className={styles.provenanceFilterInput}
              type="text"
              placeholder="Source"
              value={filterSource}
              onChange={(e) => setFilterSource(e.target.value)}
              aria-label="Filter by source"
              data-testid="broker-trade-provenance-filter-source"
            />
            <input
              className={styles.provenanceFilterInput}
              type="text"
              placeholder="Account"
              value={filterAccount}
              onChange={(e) => setFilterAccount(e.target.value)}
              aria-label="Filter by account"
              data-testid="broker-trade-provenance-filter-account"
            />
            <label className={styles.provenanceFilterCheckLabel}>
              <input
                type="checkbox"
                checked={filterPnlOnly}
                onChange={(e) => setFilterPnlOnly(e.target.checked)}
                data-testid="broker-trade-provenance-filter-pnl-only"
              />
              <span>P&L present only</span>
            </label>
            <div className={styles.provenanceFilterActions}>
              <button
                type="button"
                className={styles.secondaryButton}
                onClick={exportFilteredAsCsv}
                data-testid="broker-trade-provenance-export-csv"
              >
                Export CSV
              </button>
              <button
                type="button"
                className={styles.secondaryButton}
                onClick={exportFilteredAsJson}
                data-testid="broker-trade-provenance-export-json"
              >
                Export JSON
              </button>
            </div>
          </div>

          <div className={styles.auditTableWrapper}>
            <table className={styles.table}>
              <thead className={styles.thead}>
                <tr>
                  <th className={styles.th}>Time</th>
                  <th className={styles.th}>Fingerprint</th>
                  <th className={styles.th}>Symbol</th>
                  <th className={styles.th}>Side</th>
                  <th className={styles.th}>Qty</th>
                  <th className={styles.th}>Price</th>
                  <th className={styles.th}>Realized P&L</th>
                  <th className={styles.th}>Account</th>
                  <th className={styles.th}>Mode</th>
                  <th className={styles.th}>Source</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((entry, idx) => (
                  <tr
                    key={`${entry.event_fingerprint}-${idx}`}
                    className={`${styles.tr} ${styles.provenanceRow}`}
                    data-testid="broker-trade-provenance-row"
                    onClick={() => setSelectedEntry(entry)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => e.key === "Enter" && setSelectedEntry(entry)}
                    aria-label={`View details for ${entry.symbol ?? "trade"} ${entry.event_fingerprint}`}
                  >
                    <td className={styles.td}>{formatTimestamp(entry.trade_ts ?? entry.created_at)}</td>
                    <td className={styles.tdMuted}>{entry.event_fingerprint}</td>
                    <td className={styles.tdTicker}>{entry.symbol ?? "-"}</td>
                    <td className={styles.td}>
                      <span className={getSideBadgeClass(entry.side)}>{entry.side ?? "-"}</span>
                    </td>
                    <td className={styles.td}>{entry.quantity ?? "-"}</td>
                    <td className={styles.td}>{entry.fill_price != null ? formatMoney(entry.fill_price) : "-"}</td>
                    <td className={getPnlClassName(entry.realized_pnl)}>
                      {entry.realized_pnl != null ? formatMoney(entry.realized_pnl) : "-"}
                    </td>
                    <td className={styles.td}>{entry.account_id ?? "-"}</td>
                    <td className={styles.td}>{provenance.data.broker_mode?.mode ?? "unknown"}</td>
                    <td className={styles.tdMuted}>{entry.source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {filtered.length === 0 && entries.length > 0 && (
            <div className={styles.auditEmpty} data-testid="broker-trade-provenance-filtered-empty">
              No events match the current filters.
            </div>
          )}
        </>
      )}

      {selectedEntry !== null && (
        <div
          className={styles.provenanceDrawerOverlay}
          data-testid="broker-trade-provenance-drawer-overlay"
          onClick={() => setSelectedEntry(null)}
          role="presentation"
        >
          <aside
            className={styles.provenanceDrawer}
            data-testid="broker-trade-provenance-drawer"
            onClick={(e) => e.stopPropagation()}
          >
            <div className={styles.provenanceDrawerHeader}>
              <span className={styles.provenanceDrawerTitle}>Trade Event Detail</span>
              <button
                className={styles.provenanceDrawerClose}
                onClick={() => {
                  setSelectedEntry(null);
                  setCopyState("idle");
                }}
                aria-label="Close detail drawer"
                data-testid="broker-trade-provenance-drawer-close"
              >
                X
              </button>
            </div>
            <div className={styles.provenanceDrawerActions}>
              <button
                type="button"
                className={styles.secondaryButton}
                onClick={copySelectedDetail}
                data-testid="broker-trade-provenance-drawer-copy"
              >
                Copy event detail
              </button>
              {copyState === "copied" && (
                <span className={styles.provenanceDrawerCopyState} data-testid="broker-trade-provenance-drawer-copy-state">
                  Copied.
                </span>
              )}
              {copyState === "error" && (
                <span className={styles.provenanceDrawerCopyStateError} data-testid="broker-trade-provenance-drawer-copy-state">
                  Clipboard unavailable.
                </span>
              )}
            </div>
            <dl className={styles.provenanceDrawerFields}>
              <dt>Fingerprint</dt><dd data-testid="broker-trade-provenance-drawer-fingerprint">{selectedEntry.event_fingerprint}</dd>
              <dt>Symbol</dt><dd>{selectedEntry.symbol ?? "—"}</dd>
              <dt>Side</dt><dd>{selectedEntry.side ?? "—"}</dd>
              <dt>Quantity</dt><dd>{selectedEntry.quantity ?? "—"}</dd>
              <dt>Fill Price</dt><dd>{selectedEntry.fill_price != null ? formatMoney(selectedEntry.fill_price) : "—"}</dd>
              <dt>Commission</dt><dd>{selectedEntry.commission != null ? formatMoney(selectedEntry.commission) : "—"}</dd>
              <dt>Net Amount</dt><dd>{selectedEntry.net_amount != null ? formatMoney(selectedEntry.net_amount) : "—"}</dd>
              <dt>Realized P&L</dt><dd>{selectedEntry.realized_pnl != null ? formatMoney(selectedEntry.realized_pnl) : "—"}</dd>
              <dt>Trade Time</dt><dd>{formatTimestamp(selectedEntry.trade_ts ?? selectedEntry.created_at)}</dd>
              <dt>Source</dt><dd>{selectedEntry.source}</dd>
              <dt>Account</dt><dd>{selectedEntry.account_id ?? "—"}</dd>
              <dt>Broker Provider</dt><dd>{selectedEntry.broker_provider}</dd>
              <dt>External Trade ID</dt><dd>{selectedEntry.external_trade_id ?? "—"}</dd>
              <dt>Broker Order ID</dt><dd>{selectedEntry.broker_order_id ?? "—"}</dd>
              <dt>Created At</dt><dd>{formatTimestamp(selectedEntry.created_at)}</dd>
            </dl>
            <div className={styles.provenanceDrawerReconPanel} data-testid="broker-trade-provenance-reconciliation-notes">
              <p className={styles.provenanceDrawerReconTitle}>Reconciliation Notes</p>
              <ul className={styles.provenanceDrawerReconList}>
                {reconciliationNotes.map((note, idx) => (
                  <li key={`${selectedEntry.event_fingerprint}-recon-${idx}`}>{note}</li>
                ))}
              </ul>
            </div>
          </aside>
        </div>
      )}
    </section>
  );
}