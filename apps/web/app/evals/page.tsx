"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import styles from "../../styles/pages/evals.module.css";
import { useLivePolling } from "../../lib/hooks/useLivePolling";
import { getEvalRuns, type EvalRun } from "../../lib/api";

function fmt(val: number | null, decimals = 2): string {
  return val == null ? "—" : val.toFixed(decimals);
}

function fmtDate(val: string | null): string {
  if (!val) return "—";
  return new Date(val).toLocaleString();
}

export default function EvalsPage() {
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getEvalRuns()
      .then(setRuns)
      .catch(() => setError("Failed to load eval runs."))
      .finally(() => setLoading(false));
  }, []);

  useLivePolling(async () => {
    try {
      setRuns(await getEvalRuns());
      setError(null);
    } catch {
      setError("Failed to load eval runs.");
    }
  }, 20000, { enabled: true, runImmediately: false });

  return (
    <div className={styles.page}>
      <h1 className={styles.pageTitle}>Evaluation Runs</h1>

      {error && <p className={styles.errorMsg}>{error}</p>}

      <div className={styles.panel}>
        {loading ? (
          <p className={styles.loadingMsg}>Loading…</p>
        ) : runs.length === 0 ? (
          <p className={styles.emptyMsg}>No evaluation runs found.</p>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.th}>Run ID</th>
                <th className={styles.th}>Provider</th>
                <th className={styles.th}>Score</th>
                <th className={styles.th}>Pass Rate</th>
                <th className={styles.th}>Started</th>
                <th className={styles.th}>Completed</th>
                <th className={styles.th}>Notes</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.id}>
                  <td className={styles.td}>
                    <Link href={`/prompts`} className={styles.runId} style={{ textDecoration: "none" }}>
                      {r.id.slice(0, 8)}…
                    </Link>
                  </td>
                  <td className={styles.td}>{r.provider_name ?? "—"}</td>
                  <td className={styles.td}>{fmt(r.summary_score)}</td>
                  <td className={styles.td}>{fmt(r.pass_rate)}</td>
                  <td className={styles.td}>{fmtDate(r.started_at)}</td>
                  <td className={styles.td}>{fmtDate(r.completed_at)}</td>
                  <td className={styles.td}>{r.notes ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
