"use client";

import { useState } from "react";

import { FormSection } from "../../components/FormSection";
import { JsonCard } from "../../components/JsonCard";
import { createApproval, generateSignal } from "../../lib/api";
import type { ApprovalRequestResponse, ExecutionMode, Timeframe } from "../../lib/types";

interface ApprovalFormState {
  asset: string;
  timeframe: Timeframe;
  latestPrice: string;
  executionMode: ExecutionMode;
  riskApproved: boolean;
  ttlMinutes: string;
}

const initialState: ApprovalFormState = {
  asset: "EURUSD",
  timeframe: "1h",
  latestPrice: "1.0815",
  executionMode: "confirm_live",
  riskApproved: true,
  ttlMinutes: "30",
};

function inputStyle(): React.CSSProperties {
  return {
    width: "100%",
    padding: "12px 14px",
    borderRadius: 12,
    border: "1px solid var(--control-border)",
    background: "var(--control-bg)",
    color: "var(--control-text)",
    fontSize: 15,
  };
}

function labelStyle(): React.CSSProperties {
  return {
    display: "grid",
    gap: 8,
    color: "var(--text-body)",
    fontWeight: 600,
  };
}

export default function ApprovalsPage() {
  const [form, setForm] = useState<ApprovalFormState>(initialState);
  const [result, setResult] = useState<ApprovalRequestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const ttlMinutes = Number(form.ttlMinutes);
    const latestPrice = Number(form.latestPrice);

    if (!Number.isFinite(ttlMinutes) || ttlMinutes <= 0) {
      setError("TTL minutes must be a valid number greater than 0.");
      return;
    }
    if (!Number.isFinite(latestPrice) || latestPrice <= 0) {
      setError("Latest price must be a valid positive number.");
      return;
    }

    setIsSubmitting(true);

    try {
      const signal = await generateSignal({
        asset: form.asset,
        timeframe: form.timeframe,
        latest_price: latestPrice,
        feature_snapshot: { source: "approvals-page" },
        catalyst_context: { mode: "live" },
      });

      const response = await createApproval({
        signal,
        execution_mode: form.executionMode,
        risk_approved: form.riskApproved,
        ttl_minutes: ttlMinutes,
      });
      setResult(response);
    } catch (submitError) {
      setResult(null);
      setError(submitError instanceof Error ? submitError.message : "Unknown request failure");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        padding: "32px 20px 64px",
        background: "var(--app-shell-bg)",
      }}
    >
      <div style={{ maxWidth: 980, margin: "0 auto", display: "grid", gap: 24 }}>

        <FormSection title="Approvals" description="Create an approval request via POST /approvals/create.">
          <form onSubmit={handleSubmit} style={{ display: "grid", gap: 16 }}>
            <label style={labelStyle()}>
              Asset
              <input style={inputStyle()} value={form.asset} onChange={(event) => setForm({ ...form, asset: event.target.value })} />
            </label>

            <div data-rs="two-col" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <label style={labelStyle()}>
                Timeframe
                <select
                  style={inputStyle()}
                  value={form.timeframe}
                  onChange={(event) => setForm({ ...form, timeframe: event.target.value as Timeframe })}
                >
                  <option value="15m">15m</option>
                  <option value="1h">1h</option>
                  <option value="4h">4h</option>
                  <option value="1d">1d</option>
                </select>
              </label>
            </div>

            <label style={labelStyle()}>
              Latest price
              <input
                style={inputStyle()}
                inputMode="decimal"
                step="any"
                value={form.latestPrice}
                onChange={(event) => setForm({ ...form, latestPrice: event.target.value })}
              />
            </label>

            <label style={labelStyle()}>
              Execution mode
              <select
                style={inputStyle()}
                value={form.executionMode}
                onChange={(event) => setForm({ ...form, executionMode: event.target.value as ExecutionMode })}
              >
                <option value="paper">paper</option>
                <option value="confirm_live">confirm_live</option>
                <option value="auto_live">auto_live</option>
              </select>
            </label>

            <label style={{ ...labelStyle(), gridTemplateColumns: "auto 1fr", alignItems: "center" }}>
              <input
                type="checkbox"
                checked={form.riskApproved}
                onChange={(event) => setForm({ ...form, riskApproved: event.target.checked })}
              />
              Risk approved
            </label>

            <label style={labelStyle()}>
              TTL minutes
              <input
                style={inputStyle()}
                inputMode="numeric"
                min={1}
                step={1}
                value={form.ttlMinutes}
                onChange={(event) => setForm({ ...form, ttlMinutes: event.target.value })}
              />
              <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text-muted)" }}>Whole number greater than 0</span>
            </label>

            <button
              type="submit"
              disabled={isSubmitting}
              style={{
                border: 0,
                borderRadius: 14,
                padding: "14px 18px",
                background: isSubmitting ? "color-mix(in oklab, var(--state-info) 34%, var(--surface-soft))" : "var(--state-info)",
                color: "var(--text-strong)",
                fontSize: 15,
                fontWeight: 700,
                cursor: isSubmitting ? "not-allowed" : "pointer",
              }}
            >
              {isSubmitting ? "Creating..." : "Create approval request"}
            </button>

            {error ? (
              <div style={{ padding: 14, borderRadius: 12, border: "1px solid var(--state-warning-border)", background: "var(--state-warning-soft)", color: "var(--state-warning)" }}>
                {error}
              </div>
            ) : null}
          </form>
        </FormSection>

        <JsonCard title="Approval Response" data={result} emptyText="Submit the form to view response payload." />
      </div>
    </main>
  );
}
