"use client";

import type { BrokerOrderAuditEntry } from "../../lib/api/broker";
import styles from "../../styles/pages/broker.module.css";

type AuditState =
  | { status: "loading" }
  | { status: "ready"; entries: BrokerOrderAuditEntry[] }
  | { status: "error" };

export function BrokerAuditPanel({
  audit,
  formatTimestamp,
}: {
  audit: AuditState;
  formatTimestamp: (value: string) => string;
}) {
  return (
    <section className={styles.auditPanel} data-testid="broker-audit-panel">
      <div className={styles.auditHeaderRow}>
        <h2 className={styles.sectionTitle}>Recent Broker Order Audit</h2>
        {audit.status === "ready" && (
          <span className={styles.auditCount} data-testid="broker-audit-count">
            {audit.entries.length} events
          </span>
        )}
      </div>

      {audit.status === "loading" && (
        <div className={styles.auditEmpty}>Loading audit trail...</div>
      )}

      {audit.status === "error" && (
        <div className={styles.auditEmpty}>Audit trail unavailable.</div>
      )}

      {audit.status === "ready" && audit.entries.length === 0 && (
        <div className={styles.auditEmpty}>No broker order audit events yet.</div>
      )}

      {audit.status === "ready" && audit.entries.length > 0 && (
        <div className={styles.auditTableWrapper}>
          <table className={styles.table}>
            <thead className={styles.thead}>
              <tr>
                <th className={styles.th}>Time</th>
                <th className={styles.th}>Action</th>
                <th className={styles.th}>Symbol</th>
                <th className={styles.th}>Side</th>
                <th className={styles.th}>Qty</th>
                <th className={styles.th}>Status</th>
                <th className={styles.th}>Mode</th>
                <th className={styles.th}>Order ID / Reason</th>
              </tr>
            </thead>
            <tbody>
              {audit.entries.map((entry, idx) => (
                <tr key={`${entry.ts}-${idx}`} className={styles.tr} data-testid="broker-audit-row">
                  <td className={styles.td}>{formatTimestamp(entry.ts)}</td>
                  <td className={styles.td}>{entry.action}</td>
                  <td className={styles.tdTicker}>{entry.ticker}</td>
                  <td className={styles.td}>{entry.side}</td>
                  <td className={styles.td}>{entry.quantity ?? "-"}</td>
                  <td className={styles.td}>{entry.status}</td>
                  <td className={styles.td}>{entry.dry_run ? "Dry Run" : "Submit"}</td>
                  <td className={styles.tdMuted}>{entry.broker_order_id ?? entry.reason ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}