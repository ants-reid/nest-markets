import type {
  ApprovalCreateRequest,
  ApprovalRequestResponse,
  HealthStatusResponse,
  RiskDecisionResponse,
  RiskEvaluateRequest,
  SignalResponse,
  WorkflowRunRequest,
  WorkflowRunResponse,
} from "../types";
import { apiRequest } from "./core";

export interface GenerateSignalRequest {
  asset: string;
  timeframe: string;
  latest_price: number;
  feature_snapshot?: Record<string, unknown>;
  catalyst_context?: Record<string, unknown>;
  risk_notes?: string | null;
}

export async function getHealthStatus(): Promise<HealthStatusResponse> {
  return apiRequest<HealthStatusResponse>("/health", { method: "GET" });
}

export async function runWorkflow(payload: WorkflowRunRequest): Promise<WorkflowRunResponse> {
  return apiRequest<WorkflowRunResponse>("/workflow/run", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function generateSignal(payload: GenerateSignalRequest): Promise<SignalResponse> {
  return apiRequest<SignalResponse>("/signals/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function evaluateRisk(payload: RiskEvaluateRequest): Promise<RiskDecisionResponse> {
  return apiRequest<RiskDecisionResponse>("/risk/evaluate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function createApproval(payload: ApprovalCreateRequest): Promise<ApprovalRequestResponse> {
  return apiRequest<ApprovalRequestResponse>("/approvals/create", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function approveApprovalRequest(requestId: string): Promise<ApprovalRequestResponse> {
  return apiRequest<ApprovalRequestResponse>(`/approvals/${requestId}/approve`, { method: "POST" });
}

export async function rejectApprovalRequest(requestId: string): Promise<ApprovalRequestResponse> {
  return apiRequest<ApprovalRequestResponse>(`/approvals/${requestId}/reject`, { method: "POST" });
}
