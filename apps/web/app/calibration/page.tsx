"use client";

export default function CalibrationPage() {
  return (
    <main style={{ minHeight: "100vh", background: "var(--app-shell-bg)", fontFamily: "var(--font-base)", color: "var(--text-body)" }}>
      <div style={{ maxWidth: 860, margin: "0 auto", padding: "2rem 1.5rem" }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--text-strong)", marginBottom: "0.375rem" }}>Score Calibration</h1>
        <p style={{ color: "var(--text-muted)", fontSize: "0.875rem", marginBottom: "1.75rem" }}>
          Compare predicted probabilities against observed outcome rates.
        </p>
        <div style={{ background: "var(--surface-soft)", border: "1px solid var(--surface-border)", borderRadius: 12, padding: "2rem", textAlign: "center" }}>
          <p style={{ color: "var(--text-muted)", fontSize: "0.875rem", marginBottom: "0.5rem" }}>
            Calibration curve visualisation
          </p>
          <p style={{ color: "var(--text-muted)", fontSize: "0.8125rem" }}>
            Connect to <code style={{ fontFamily: "monospace", background: "var(--surface-border)", padding: "2px 6px", borderRadius: 4 }}>/scoring/calibration</code> to populate.
          </p>
        </div>
      </div>
    </main>
  );
}
