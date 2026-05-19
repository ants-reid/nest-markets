"use client";

import type { WorkflowRunResponse } from "../lib/types";

interface WorkflowResultCardProps {
  result: WorkflowRunResponse | null;
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "grid", gap: 4 }}>
      <span style={{ color: "var(--text-muted)", fontSize: 11, textTransform: "uppercase", letterSpacing: 1.2, fontWeight: 700 }}>
        {label}
      </span>
      <span style={{ color: "var(--text-strong)", fontFamily: "Menlo, Monaco, monospace", fontSize: 13, fontVariantNumeric: "tabular-nums" }}>{value}</span>
    </div>
  );
}

export function WorkflowResultCard({ result }: WorkflowResultCardProps) {
  if (!result) {
    return (
      <section
        style={{
          padding: 24,
          borderRadius: 18,
          border: "1px dashed var(--surface-border)",
          background: "var(--surface-fill)",
          color: "var(--text-muted)",
        }}
      >
        Run the live workflow to see the persisted workflow summary here.
      </section>
    );
  }

  return (
    <section
      style={{
        display: "grid",
        gap: 20,
        padding: 24,
        borderRadius: 20,
        border: "1px solid var(--surface-border)",
        background: "var(--surface-fill)",
        boxShadow: "var(--surface-shadow)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
        <div>
          <h2 style={{ margin: 0, color: "var(--text-strong)", fontSize: 22, fontWeight: 800, letterSpacing: 0.1 }}>Workflow Result</h2>
          <p style={{ margin: "8px 0 0", color: "var(--text-muted)" }}>
            End-to-end workflow summary returned by the backend.
          </p>
        </div>
        <div
          style={{
            alignSelf: "flex-start",
            padding: "8px 12px",
            borderRadius: 999,
            background: result.risk_approved ? "var(--state-success-soft)" : "var(--state-danger-soft)",
            color: result.risk_approved ? "var(--state-success)" : "var(--state-danger)",
            fontWeight: 700,
            border: `1px solid ${result.risk_approved ? "var(--state-success-border)" : "var(--state-danger-border)"}`,
            letterSpacing: 0.5,
          }}
        >
          {result.risk_approved ? "Approved" : "Blocked"}
        </div>
      </div>

      <div style={{ display: "grid", gap: 16, gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
        <Field label="Signal ID" value={result.signal_id} />
        <Field label="Risk Approved" value={String(result.risk_approved)} />
        <Field label="Execution Mode" value={result.selected_execution_mode} />
        <Field label="Approval Request ID" value={result.approval_request_id ?? "None"} />
        <Field label="Paper Execution ID" value={result.paper_execution_id ?? "None"} />
      </div>

      <div style={{ display: "grid", gap: 8 }}>
        <span style={{ color: "var(--text-muted)", fontSize: 11, textTransform: "uppercase", letterSpacing: 1.2, fontWeight: 700 }}>
          Blocked Reasons
        </span>
        {result.blocked_reasons.length === 0 ? (
          <span style={{ color: "var(--text-muted)" }}>None</span>
        ) : (
          <ul style={{ margin: 0, paddingLeft: 18, color: "var(--text-strong)" }}>
            {result.blocked_reasons.map((reason) => (
              <li key={reason} style={{ marginBottom: 4 }}>
                {reason}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div style={{ display: "grid", gap: 8 }}>
        <span style={{ color: "var(--text-muted)", fontSize: 11, textTransform: "uppercase", letterSpacing: 1.2, fontWeight: 700 }}>
          Live Execution Result
        </span>
        {result.live_execution_result ? (
          <div
            style={{
              display: "grid",
              gap: 8,
              padding: 16,
              borderRadius: 14,
              background: "var(--surface-soft)",
              border: "1px solid var(--surface-border)",
            }}
          >
            <Field label="Accepted" value={String(result.live_execution_result.accepted)} />
            <Field label="Status" value={result.live_execution_result.status} />
            <Field label="Reason" value={result.live_execution_result.reason} />
          </div>
        ) : (
          <span style={{ color: "var(--text-muted)" }}>No live execution result returned.</span>
        )}
      </div>
    </section>
  );
}