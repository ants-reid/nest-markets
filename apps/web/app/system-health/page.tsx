"use client";

// MH-MON-06 — System Health page.
// View-only surface. Reads:
//   - GET /health/services  (MH-MON-01)
//   - GET /health/safety    (MH-MON-04)
// No mutations, no auto/live trading toggles. The drift lock notice is
// rendered explicitly so operators see the safety posture inline.

import { useCallback, useEffect, useState } from "react";

import {
  getHealthServices,
  getHealthSafety,
  type HealthService,
  type HealthServicesResponse,
  type ProbeStatus,
  type TradingSafetyDecisionDTO,
} from "../../lib/api/systemHealth";
import styles from "../../styles/pages/system-health.module.css";

const STATUS_BADGE_CLASS: Record<ProbeStatus, string> = {
  ok: styles.statusOk,
  degraded: styles.statusDegraded,
  down: styles.statusDown,
  unknown: styles.statusUnknown,
  error: styles.statusError,
};

function StatusBadge({ status }: { status: ProbeStatus }) {
  const cls = STATUS_BADGE_CLASS[status] ?? styles.statusUnknown;
  return <span className={`${styles.statusBadge} ${cls}`}>{status}</span>;
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

function formatLatency(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return "—";
  return `${ms.toFixed(1)} ms`;
}

export default function SystemHealthPage() {
  const [services, setServices] = useState<HealthServicesResponse | null>(null);
  const [safety, setSafety] = useState<TradingSafetyDecisionDTO | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [svc, saf] = await Promise.all([getHealthServices(), getHealthSafety()]);
      setServices(svc);
      setSafety(saf);
      setLastRefreshed(new Date());
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  const overall: ProbeStatus = services?.overall ?? "unknown";
  const rows: HealthService[] = services?.services ?? [];

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>System Health</h1>
            <p className={styles.subtitle}>
              Read-only diagnostic view. Aggregates registered service probes and the
              advisory Trading Safety Decision. No control surfaces are exposed here.
            </p>
          </div>
          <div className={styles.refreshBar}>
            {lastRefreshed && (
              <span className={styles.refreshTimestamp}>
                Updated {lastRefreshed.toLocaleTimeString()}
              </span>
            )}
            <button
              type="button"
              className={styles.refreshButton}
              onClick={() => void loadAll()}
              disabled={loading}
            >
              {loading ? "Refreshing…" : "Refresh"}
            </button>
          </div>
        </header>

        {error && <div className={styles.errorBanner}>Failed to load: {error}</div>}

        <section className={styles.section} aria-labelledby="services-title">
          <h2 id="services-title" className={styles.sectionTitle}>
            Service Probes
          </h2>
          <div className={styles.overallRow}>
            <span>Overall:</span>
            <StatusBadge status={overall} />
            {services && (
              <span className={styles.refreshTimestamp}>
                {services.services.length} of {services.registered.length} registered
              </span>
            )}
          </div>
          {loading && !services ? (
            <div className={styles.loading}>Loading probes…</div>
          ) : (
            <table className={styles.serviceTable}>
              <thead>
                <tr>
                  <th>Service</th>
                  <th>Status</th>
                  <th>Latency</th>
                  <th>Checked</th>
                  <th>Detail</th>
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 ? (
                  <tr>
                    <td colSpan={5} className={styles.emptyRow}>
                      No probes registered.
                    </td>
                  </tr>
                ) : (
                  rows.map((row) => (
                    <tr key={row.name}>
                      <td>{row.name}</td>
                      <td>
                        <StatusBadge status={row.status} />
                      </td>
                      <td>{formatLatency(row.latency_ms)}</td>
                      <td>{formatTimestamp(row.checked_at)}</td>
                      <td className={styles.detailCell}>{row.detail ?? "—"}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}
        </section>

        <section className={styles.section} aria-labelledby="safety-title">
          <h2 id="safety-title" className={styles.sectionTitle}>
            Trading Safety Decision
          </h2>
          {loading && !safety ? (
            <div className={styles.loading}>Loading safety decision…</div>
          ) : safety ? (
            <>
              <div className={styles.overallRow}>
                <span>Safe to enable enforcement:</span>
                <StatusBadge status={safety.safe_to_enable_enforcement ? "ok" : "down"} />
              </div>
              <div className={styles.metaGrid}>
                <div>
                  <div className={styles.metaLabel}>Trading mode</div>
                  <div className={styles.metaValue}>{safety.trading_mode ?? "—"}</div>
                </div>
                <div>
                  <div className={styles.metaLabel}>Auto trading allowed</div>
                  <div className={styles.metaValue}>
                    {safety.auto_trading_allowed === undefined ||
                    safety.auto_trading_allowed === null
                      ? "—"
                      : String(safety.auto_trading_allowed)}
                  </div>
                </div>
                <div>
                  <div className={styles.metaLabel}>Emergency stop</div>
                  <div className={styles.metaValue}>
                    {safety.emergency_stop_active === undefined ||
                    safety.emergency_stop_active === null
                      ? "—"
                      : String(safety.emergency_stop_active)}
                  </div>
                </div>
                <div>
                  <div className={styles.metaLabel}>Evaluated at</div>
                  <div className={styles.metaValue}>{formatTimestamp(safety.evaluated_at)}</div>
                </div>
              </div>
              {safety.blocking_reasons.length > 0 && (
                <>
                  <div className={styles.metaLabel} style={{ marginTop: "0.75rem" }}>
                    Blocking reasons
                  </div>
                  <ul className={styles.reasonsList}>
                    {safety.blocking_reasons.map((reason, idx) => (
                      <li key={`block-${idx}`}>{reason}</li>
                    ))}
                  </ul>
                </>
              )}
              {safety.advisory_reasons.length > 0 && (
                <>
                  <div className={styles.metaLabel} style={{ marginTop: "0.75rem" }}>
                    Advisory reasons
                  </div>
                  <ul className={styles.reasonsList}>
                    {safety.advisory_reasons.map((reason, idx) => (
                      <li key={`adv-${idx}`}>{reason}</li>
                    ))}
                  </ul>
                </>
              )}
              <div className={styles.driftLockNotice}>
                Drift lock active: this view is advisory only. Actual enforcement gates
                live in <code>trading_control_service</code> and{" "}
                <code>broker_mode_guard</code>. Auto-paper enforcement, auto trading,
                and live trading remain OFF.
              </div>
            </>
          ) : (
            <div className={styles.emptyRow}>No safety decision available.</div>
          )}
        </section>
      </div>
    </main>
  );
}
