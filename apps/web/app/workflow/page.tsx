"use client";

import Link from "next/link";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import { OperatorNotificationSurface } from "../../components/OperatorNotificationSurface";
import { WorkflowResultCard } from "../../components/WorkflowResultCard";
import { approveApprovalRequest, rejectApprovalRequest, runWorkflow } from "../../lib/api";
import { GLOBAL_EXECUTION_MODE_KEY } from "../../components/PersonalDashboard";
import type {
  ApprovalRequestResponse,
  ExecutionMode,
  Timeframe,
  WorkflowRunRequest,
  WorkflowRunResponse,
} from "../../lib/types";

interface WorkflowFormState {
  asset: string;
  timeframe: Timeframe;
  latestPrice: string;
  spreadBps: string;
  dailyDrawdownPct: string;
  consecutiveLosses: string;
  minutesSinceLastLoss: string;
  correlatedExposureCount: string;
  marketQualityFlag: boolean;
  accountEquity: string;
  riskNotes: string;
}

const initialState: WorkflowFormState = {
  asset: "EURUSD",
  timeframe: "1h",
  latestPrice: "1.0815",
  spreadBps: "10",
  dailyDrawdownPct: "1",
  consecutiveLosses: "0",
  minutesSinceLastLoss: "",
  correlatedExposureCount: "0",
  marketQualityFlag: true,
  accountEquity: "50000",
  riskNotes: "Live workflow run",
};

interface ApprovalViewState {
  requestId: string;
  status: string;
  asset: string;
  timeframe: string;
  executionMode: string;
  createdAt?: string;
  expiresAt?: string;
}

function mapApprovalResponseToView(response: ApprovalRequestResponse): ApprovalViewState {
  return {
    requestId: response.request_id,
    status: response.status,
    asset: response.asset,
    timeframe: response.timeframe,
    executionMode: response.execution_mode,
    createdAt: response.created_at,
    expiresAt: response.expires_at,
  };
}

function formatDateLabel(value?: string): string {
  if (!value) {
    return "n/a";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString();
}

function labelStyle(): React.CSSProperties {
  return {
    display: "grid",
    gap: 8,
    color: "var(--text-body)",
    fontWeight: 600,
  };
}

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

function WorkflowPageContent() {
  const searchParams = useSearchParams();
  const urlAsset = searchParams.get("asset");
  const urlExecutionId = searchParams.get("executionId");
  const urlStatus = searchParams.get("status");

  const [form, setForm] = useState<WorkflowFormState>(initialState);
  const [result, setResult] = useState<WorkflowRunResponse | null>(null);
  const [approval, setApproval] = useState<ApprovalViewState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [approvalError, setApprovalError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [approvalAction, setApprovalAction] = useState<"approve" | "reject" | null>(null);

  useEffect(() => {
    if (!urlAsset) {
      return;
    }

    setForm((current) => {
      if (current.asset === urlAsset) {
        return current;
      }
      return { ...current, asset: urlAsset };
    });
  }, [urlAsset]);

  const hasUrlContext = useMemo(() => {
    return Boolean(urlAsset || urlExecutionId || urlStatus);
  }, [urlAsset, urlExecutionId, urlStatus]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setApprovalError(null);

    const latestPrice = Number(form.latestPrice);
    const spreadBps = Number(form.spreadBps);
    const dailyDrawdownPct = Number(form.dailyDrawdownPct);
    const consecutiveLosses = Number(form.consecutiveLosses);
    const correlatedExposureCount = Number(form.correlatedExposureCount);
    const accountEquity = Number(form.accountEquity);

    if (!Number.isFinite(latestPrice) || latestPrice < 0) {
      setError("Latest price must be a valid number and >= 0.");
      return;
    }
    if (!Number.isFinite(spreadBps) || spreadBps < 0) {
      setError("Spread bps must be a valid number and >= 0.");
      return;
    }
    if (!Number.isFinite(dailyDrawdownPct) || dailyDrawdownPct < 0) {
      setError("Daily drawdown % must be a valid number and >= 0.");
      return;
    }
    if (!Number.isFinite(consecutiveLosses) || consecutiveLosses < 0) {
      setError("Consecutive losses must be a valid number and >= 0.");
      return;
    }
    if (!Number.isFinite(correlatedExposureCount) || correlatedExposureCount < 0) {
      setError("Correlated exposure count must be a valid number and >= 0.");
      return;
    }
    if (!Number.isFinite(accountEquity) || accountEquity < 0) {
      setError("Account equity must be a valid number and >= 0.");
      return;
    }
    if (form.minutesSinceLastLoss !== "") {
      const minutesSinceLastLoss = Number(form.minutesSinceLastLoss);
      if (!Number.isFinite(minutesSinceLastLoss) || minutesSinceLastLoss < 0) {
        setError("Minutes since last loss must be a valid number and >= 0.");
        return;
      }
    }

    setIsSubmitting(true);

    // Read execution mode from the global setting saved on the dashboard
    const savedMode = typeof window !== "undefined" ? window.localStorage.getItem(GLOBAL_EXECUTION_MODE_KEY) : null;
    const requestedExecutionMode: ExecutionMode =
      savedMode === "paper" || savedMode === "confirm_live" || savedMode === "auto_live"
        ? savedMode
        : "paper";

    const payload: WorkflowRunRequest = {
      signal_input: {
        asset: form.asset,
        timeframe: form.timeframe,
        latest_price: latestPrice,
        feature_snapshot: { source: "dashboard-shell", price_hint: latestPrice },
        catalyst_context: { mode: "live", page: "workflow" },
        risk_notes: form.riskNotes || null,
      },
      risk_context: {
        spread_bps: spreadBps,
        daily_drawdown_pct: dailyDrawdownPct,
        consecutive_losses: consecutiveLosses,
        minutes_since_last_loss: form.minutesSinceLastLoss === "" ? null : Number(form.minutesSinceLastLoss),
        correlated_exposure_count: correlatedExposureCount,
        market_quality_flag: form.marketQualityFlag,
        account_equity: accountEquity,
        requested_execution_mode: requestedExecutionMode,
      },
    };

    try {
      const workflowResult = await runWorkflow(payload);
      setResult(workflowResult);
      if (workflowResult.approval_request_id) {
        setApproval({
          requestId: workflowResult.approval_request_id,
          status: "pending",
          asset: form.asset,
          timeframe: form.timeframe,
          executionMode: workflowResult.selected_execution_mode,
        });
      } else {
        setApproval(null);
      }
    } catch (submitError) {
      setResult(null);
      setApproval(null);
      setError(submitError instanceof Error ? submitError.message : "Unknown request failure");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleApprovalAction(action: "approve" | "reject") {
    if (!approval) {
      return;
    }

    setApprovalError(null);
    setApprovalAction(action);

    try {
      const response =
        action === "approve"
          ? await approveApprovalRequest(approval.requestId)
          : await rejectApprovalRequest(approval.requestId);
      setApproval(mapApprovalResponseToView(response));
    } catch (actionError) {
      setApprovalError(actionError instanceof Error ? actionError.message : "Unknown approval action failure");
    } finally {
      setApprovalAction(null);
    }
  }

  const approvalRequired = Boolean(result?.approval_request_id);
  const isPendingApproval = approval?.status.toLowerCase() === "pending";

  return (
    <main
      style={{
        minHeight: "100vh",
        padding: "32px 20px 64px",
        background: "var(--app-shell-bg)",
      }}
    >
      <div style={{ maxWidth: 1080, margin: "0 auto", display: "grid", gap: 24 }}>

        <OperatorNotificationSurface title="Operator Notifications" maxItems={3} />

        <section
          data-rs="panel-pad"
          style={{
            display: "grid",
            gap: 10,
            padding: 28,
            borderRadius: 24,
            background: "var(--surface-fill)",
            border: "1px solid var(--surface-border)",
            boxShadow: "var(--surface-shadow)",
          }}
        >
          <span style={{ color: "var(--text-muted)", fontSize: 13, textTransform: "uppercase", letterSpacing: 1.1 }}>
            Live LLM mode
          </span>
          <h1 data-rs="hero-title" style={{ margin: 0, color: "var(--text-strong)", fontSize: 40, lineHeight: 1.05 }}>Workflow Runner</h1>
          <p style={{ margin: 0, color: "var(--text-muted)", lineHeight: 1.6, maxWidth: 760 }}>
            Calls <code>/workflow/run</code> and routes through signal → risk → execution using live signal generation.
          </p>
          {hasUrlContext ? (
            <div
              style={{
                marginTop: 6,
                padding: 12,
                borderRadius: 12,
                border: "1px solid var(--state-info-border)",
                background: "var(--state-info-soft)",
                color: "var(--text-body)",
                fontSize: 14,
              }}
            >
              <div style={{ fontWeight: 700, marginBottom: 4 }}>Context from navigation</div>
              {urlAsset ? <div>Asset prefill: {urlAsset}</div> : null}
              {urlExecutionId ? <div>Execution reference: {urlExecutionId}</div> : null}
              {urlStatus ? <div>Execution status: {urlStatus}</div> : null}
              {urlExecutionId ? (
                <div style={{ marginTop: 6 }}>
                  <Link
                    href={`/execution?executionId=${encodeURIComponent(urlExecutionId)}${urlStatus ? `&status=${encodeURIComponent(urlStatus)}` : ""}${urlAsset ? `&asset=${encodeURIComponent(urlAsset)}` : ""}`}
                    style={{ color: "var(--state-info)", fontWeight: 700, textDecoration: "none" }}
                  >
                    Return to execution detail context
                  </Link>
                </div>
              ) : null}
            </div>
          ) : null}
        </section>

        <section data-rs="split-main" style={{ display: "grid", gap: 24, gridTemplateColumns: "minmax(320px, 420px) minmax(0, 1fr)" }}>
          <form
            onSubmit={handleSubmit}
            style={{
              display: "grid",
              gap: 16,
              padding: 24,
              borderRadius: 20,
              background: "var(--surface-fill)",
              border: "1px solid var(--surface-border)",
              boxShadow: "var(--surface-shadow)",
            }}
          >
            <h2 style={{ margin: 0, color: "var(--text-strong)", fontSize: 24 }}>Request</h2>

            <label style={labelStyle()}>
              Asset
              <input style={inputStyle()} value={form.asset} onChange={(event) => setForm({ ...form, asset: event.target.value })} />
            </label>

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

            <label style={labelStyle()}>
              Latest price
              <input
                style={inputStyle()}
                inputMode="decimal"
                min={0}
                step="any"
                value={form.latestPrice}
                onChange={(event) => setForm({ ...form, latestPrice: event.target.value })}
              />
              <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text-muted)" }}>Number, 0 or more</span>
            </label>

            <label style={labelStyle()}>
              Spread bps
              <input
                style={inputStyle()}
                inputMode="decimal"
                min={0}
                step="any"
                value={form.spreadBps}
                onChange={(event) => setForm({ ...form, spreadBps: event.target.value })}
              />
              <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text-muted)" }}>Number, 0 or more</span>
            </label>

            <label style={labelStyle()}>
              Daily drawdown %
              <input
                style={inputStyle()}
                inputMode="decimal"
                min={0}
                step="any"
                value={form.dailyDrawdownPct}
                onChange={(event) => setForm({ ...form, dailyDrawdownPct: event.target.value })}
              />
              <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text-muted)" }}>Number, 0 or more</span>
            </label>

            <label style={labelStyle()}>
              Consecutive losses
              <input
                style={inputStyle()}
                inputMode="numeric"
                min={0}
                step={1}
                value={form.consecutiveLosses}
                onChange={(event) => setForm({ ...form, consecutiveLosses: event.target.value })}
              />
              <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text-muted)" }}>Whole number, 0 or more</span>
            </label>

            <label style={labelStyle()}>
              Minutes since last loss
              <input
                style={inputStyle()}
                inputMode="numeric"
                min={0}
                step={1}
                value={form.minutesSinceLastLoss}
                onChange={(event) => setForm({ ...form, minutesSinceLastLoss: event.target.value })}
                placeholder="Leave blank for null"
              />
              <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text-muted)" }}>Whole number, 0 or more</span>
            </label>

            <label style={labelStyle()}>
              Correlated exposure count
              <input
                style={inputStyle()}
                inputMode="numeric"
                min={0}
                step={1}
                value={form.correlatedExposureCount}
                onChange={(event) => setForm({ ...form, correlatedExposureCount: event.target.value })}
              />
              <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text-muted)" }}>Whole number, 0 or more</span>
            </label>

            <label style={labelStyle()}>
              Account equity
              <input
                style={inputStyle()}
                inputMode="decimal"
                min={0}
                step="any"
                value={form.accountEquity}
                onChange={(event) => setForm({ ...form, accountEquity: event.target.value })}
              />
              <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text-muted)" }}>Number, 0 or more</span>
            </label>

            <label style={labelStyle()}>
              Execution mode
              <span style={{ ...inputStyle(), display: "flex", alignItems: "center", gap: "0.5rem", color: "var(--text-muted)", fontSize: 13 }}>
                Set on the{" "}
                <Link href="/" style={{ color: "var(--accent-primary)", textDecoration: "underline" }}>
                  Dashboard
                </Link>
              </span>
            </label>

            <label style={{ ...labelStyle(), gridTemplateColumns: "auto 1fr", alignItems: "center" }}>
              <input
                type="checkbox"
                checked={form.marketQualityFlag}
                onChange={(event) => setForm({ ...form, marketQualityFlag: event.target.checked })}
              />
              Market quality flag is good
            </label>

            <label style={labelStyle()}>
              Risk notes
              <textarea
                style={{ ...inputStyle(), minHeight: 96, resize: "vertical" }}
                value={form.riskNotes}
                onChange={(event) => setForm({ ...form, riskNotes: event.target.value })}
              />
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
              {isSubmitting ? "Running workflow..." : "Run live workflow"}
            </button>

            {error ? (
              <div
                style={{
                  padding: 14,
                  borderRadius: 12,
                  background: "var(--state-warning-soft)",
                  color: "var(--state-warning)",
                  border: "1px solid var(--state-warning-border)",
                }}
              >
                {error}
              </div>
            ) : null}
          </form>

          <WorkflowResultCard result={result} />
        </section>

        <section
          style={{
            display: "grid",
            gap: 16,
            padding: 24,
            borderRadius: 20,
            border: "1px solid var(--surface-border)",
            background: "var(--surface-fill)",
            boxShadow: "var(--surface-shadow)",
          }}
        >
          <h2 style={{ margin: 0, color: "var(--text-strong)", fontSize: 24 }}>Approvals and Handoff</h2>

          {isSubmitting ? (
            <p style={{ margin: 0, color: "var(--text-muted)" }}>Loading workflow result...</p>
          ) : null}

          {!result && !isSubmitting ? (
            <p style={{ margin: 0, color: "var(--text-muted)" }}>
              Run workflow to view approval-required state and actions.
            </p>
          ) : null}

          {result ? (
            <div style={{ display: "grid", gap: 12 }}>
              <div
                style={{
                  display: "grid",
                  gap: 8,
                  padding: 14,
                  borderRadius: 12,
                  border: "1px solid var(--surface-border)",
                  background: "var(--surface-soft)",
                }}
              >
                <div style={{ color: "var(--text-body)", fontWeight: 700 }}>Workflow State</div>
                <div style={{ color: "var(--text-muted)" }}>Selected execution mode: {result.selected_execution_mode}</div>
                <div style={{ color: "var(--text-muted)" }}>Risk approved: {String(result.risk_approved)}</div>
                <div style={{ color: "var(--text-muted)" }}>Approval required: {approvalRequired ? "yes" : "no"}</div>
                <div style={{ color: "var(--text-muted)" }}>
                  Blocked state: {result.blocked_reasons.length > 0 ? result.blocked_reasons.join(", ") : "not blocked"}
                </div>
              </div>

              {approval ? (
                <div
                  style={{
                    display: "grid",
                    gap: 10,
                    padding: 14,
                    borderRadius: 12,
                    border: "1px solid var(--surface-border)",
                    background: "var(--control-bg)",
                  }}
                >
                  <div style={{ color: "var(--text-body)", fontWeight: 700 }}>Approval Request</div>
                  <div style={{ color: "var(--text-muted)" }}>Request ID: {approval.requestId}</div>
                  <div style={{ color: "var(--text-muted)" }}>Status: {approval.status}</div>
                  <div style={{ color: "var(--text-muted)" }}>Asset: {approval.asset}</div>
                  <div style={{ color: "var(--text-muted)" }}>Timeframe: {approval.timeframe}</div>
                  <div style={{ color: "var(--text-muted)" }}>Execution mode: {approval.executionMode}</div>
                  <div style={{ color: "var(--text-muted)" }}>Created: {formatDateLabel(approval.createdAt)}</div>
                  <div style={{ color: "var(--text-muted)" }}>Expires: {formatDateLabel(approval.expiresAt)}</div>

                  {isPendingApproval ? (
                    <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 6 }}>
                      <button
                        type="button"
                        disabled={Boolean(approvalAction)}
                        onClick={() => handleApprovalAction("approve")}
                        style={{
                          border: 0,
                          borderRadius: 12,
                          padding: "10px 14px",
                          background: approvalAction ? "var(--text-muted)" : "var(--state-success)",
                          color: "var(--surface-soft)",
                          fontWeight: 700,
                          cursor: approvalAction ? "not-allowed" : "pointer",
                        }}
                      >
                        {approvalAction === "approve" ? "Approving..." : "Approve"}
                      </button>
                      <button
                        type="button"
                        disabled={Boolean(approvalAction)}
                        onClick={() => handleApprovalAction("reject")}
                        style={{
                          border: 0,
                          borderRadius: 12,
                          padding: "10px 14px",
                          background: approvalAction ? "var(--text-muted)" : "var(--state-danger)",
                          color: "var(--surface-soft)",
                          fontWeight: 700,
                          cursor: approvalAction ? "not-allowed" : "pointer",
                        }}
                      >
                        {approvalAction === "reject" ? "Rejecting..." : "Reject"}
                      </button>
                    </div>
                  ) : (
                    <div
                      style={{
                        marginTop: 6,
                        color: "var(--text-body)",
                        background: "var(--surface-soft)",
                        border: "1px solid var(--surface-border)",
                        borderRadius: 12,
                        padding: 12,
                      }}
                    >
                      Approval is terminal with status: {approval.status}
                    </div>
                  )}
                </div>
              ) : (
                <div
                  style={{
                    padding: 14,
                    borderRadius: 12,
                    border: "1px dashed var(--surface-border)",
                    color: "var(--text-muted)",
                    background: "var(--control-bg)",
                  }}
                >
                  <div style={{ marginBottom: 10 }}>No pending approval returned by this workflow run.</div>
                </div>
              )}

              <div
                style={{
                  display: "grid",
                  gap: 8,
                  padding: 14,
                  borderRadius: 12,
                  border: "1px solid var(--surface-border)",
                  background: "var(--surface-soft)",
                }}
              >
                <div style={{ color: "var(--text-body)", fontWeight: 700 }}>Resulting Handoff State</div>
                {result.paper_execution_id ? (
                  <div style={{ color: "var(--text-muted)" }}>Paper execution handoff completed: {result.paper_execution_id}</div>
                ) : approval ? (
                  <div style={{ color: "var(--text-muted)" }}>
                    {approval.status.toLowerCase() === "approved"
                      ? "Approval complete. Request is approved for downstream execution handoff."
                      : approval.status.toLowerCase() === "rejected"
                        ? "Approval rejected. Workflow is terminal and no execution handoff occurs."
                        : `Awaiting approval decision for request ${approval.requestId}.`}
                  </div>
                ) : (
                  <div style={{ color: "var(--text-muted)" }}>No execution handoff occurred for this workflow run.</div>
                )}
              </div>
            </div>
          ) : null}

          {approvalError ? (
            <div
              style={{
                padding: 14,
                borderRadius: 12,
                background: "var(--state-warning-soft)",
                color: "var(--state-warning)",
                border: "1px solid var(--state-warning-border)",
              }}
            >
              {approvalError}
            </div>
          ) : null}
        </section>
      </div>
    </main>
  );
}

export default function WorkflowPage() {
  return (
    <Suspense fallback={null}>
      <WorkflowPageContent />
    </Suspense>
  );
}