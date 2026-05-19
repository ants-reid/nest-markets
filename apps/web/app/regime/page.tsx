"use client";

import { useEffect, useState } from "react";
import { getRegime, type RegimeSnapshot } from "../../lib/api";
import { useLivePolling } from "../../lib/hooks/useLivePolling";

const REGIME_COLOR: Record<string, string> = {
  trend: "var(--state-success)",
  breakout: "var(--accent-primary)",
  range: "var(--state-warning)",
  reversal: "var(--state-danger)",
  default: "var(--text-muted)",
};

export default function RegimePage() {
  const [snapshot, setSnapshot] = useState<RegimeSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setSnapshot(await getRegime());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load regime.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);
  useLivePolling(() => load(), 15000, { enabled: true, runImmediately: false });

  const regimeColor = snapshot
    ? (REGIME_COLOR[snapshot.regime] ?? REGIME_COLOR.default)
    : "var(--text-muted)";

  return (
    <main style={{ minHeight: "100vh", background: "var(--app-shell-bg)", fontFamily: "var(--font-base)", color: "var(--text-body)" }}>
      <div style={{ maxWidth: 860, margin: "0 auto", padding: "2rem 1.5rem" }}>

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.375rem" }}>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--text-strong)", margin: 0 }}>Regime Monitor</h1>
          <button
            type="button" onClick={() => void load()}
            style={{ padding: "0.375rem 0.875rem", fontSize: "0.875rem", cursor: "pointer", border: "1px solid var(--surface-border)", borderRadius: 8, background: "transparent", color: "var(--text-muted)" }}
          >
            Refresh
          </button>
        </div>
        <p style={{ color: "var(--text-muted)", fontSize: "0.875rem", marginBottom: "1.75rem" }}>
          Current market regime detected by the signal engine.
        </p>

        {loading && <p style={{ color: "var(--text-muted)" }}>Loading…</p>}
        {error && (
          <div style={{ color: "var(--state-danger)", padding: "0.75rem 1rem", background: "var(--surface-soft)", border: "1px solid var(--surface-border)", borderRadius: 10 }}>
            {error}
          </div>
        )}

        {snapshot && (
          <div style={{ background: "var(--surface-soft)", border: "1px solid var(--surface-border)", borderRadius: 14, padding: "1.75rem 2rem" }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: "1rem", marginBottom: "1rem" }}>
              <span style={{ fontSize: "2.25rem", fontWeight: 800, color: regimeColor, textTransform: "capitalize", letterSpacing: "-0.5px" }}>
                {snapshot.regime.replace(/_/g, " ")}
              </span>
              <span style={{ fontSize: "1rem", color: "var(--text-muted)", fontWeight: 500 }}>
                {(snapshot.confidence * 100).toFixed(0)}% confidence
              </span>
            </div>
            <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <div style={{ width: "100%", height: 8, borderRadius: 999, background: "var(--surface-border)", overflow: "hidden" }}>
                <div style={{ width: `${(snapshot.confidence * 100).toFixed(0)}%`, height: "100%", background: regimeColor, borderRadius: 999, transition: "width 0.4s ease" }} />
              </div>
            </div>
            <p style={{ color: "var(--text-muted)", fontSize: "0.8125rem", marginTop: "1rem" }}>
              Detected: {snapshot.detected_at.slice(0, 19).replace("T", " ")} UTC
            </p>
          </div>
        )}
      </div>
    </main>
  );
}
