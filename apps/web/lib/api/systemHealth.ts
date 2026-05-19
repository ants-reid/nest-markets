// MH-MON-06 — System Health frontend API client (read-only).
// No POST/PUT/DELETE: this module is purely diagnostic.

import { apiRequest } from "./core";

export type ProbeStatus = "ok" | "degraded" | "down" | "unknown" | "error";

export interface HealthService {
  name: string;
  status: ProbeStatus;
  detail: string | null;
  latency_ms: number | null;
  checked_at: string | null;
  extra?: Record<string, unknown> | null;
}

export interface HealthServicesResponse {
  overall: ProbeStatus;
  registered: string[];
  services: HealthService[];
}

export interface TradingSafetyDecisionDTO {
  safe_to_enable_enforcement: boolean;
  blocking_reasons: string[];
  advisory_reasons: string[];
  evaluated_at: string;
  probes_summary?: Record<string, ProbeStatus> | null;
  trading_mode?: string | null;
  auto_trading_allowed?: boolean | null;
  emergency_stop_active?: boolean | null;
  [key: string]: unknown;
}

export async function getHealthServices(): Promise<HealthServicesResponse> {
  return apiRequest<HealthServicesResponse>("/health/services", { method: "GET" });
}

export async function getHealthSafety(): Promise<TradingSafetyDecisionDTO> {
  return apiRequest<TradingSafetyDecisionDTO>("/health/safety", { method: "GET" });
}
