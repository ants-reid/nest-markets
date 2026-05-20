import { apiRequest } from "./core";

export type CockpitModeId =
  | "learning"
  | "manual"
  | "auto_paper"
  | "assisted_live"
  | "live"
  | "auto_live";

export interface CockpitModeOption {
  id: CockpitModeId;
  label: string;
  status: "active" | "available" | "locked";
  selectable: boolean;
  locked: boolean;
  reason: string;
  risk_note: string;
  allowed_actions: string[];
  blocked_actions: string[];
  safety_gates: string[];
}

export interface CockpitModeSafetyState {
  live_trading_enabled: boolean;
  auto_live_enabled: boolean;
  real_money_enabled: boolean;
  paper_order_submission_allowed: boolean;
  live_order_submission_allowed: boolean;
  auto_trading_allowed: boolean;
  emergency_stop_active: boolean;
  trading_mode: string;
  execution_control: string;
  arming_state: string;
  reasons: string[];
}

export interface CockpitModeResponse {
  current_mode: CockpitModeId;
  selectable_modes: CockpitModeId[];
  locked_modes: CockpitModeId[];
  modes: CockpitModeOption[];
  global_safety_state: CockpitModeSafetyState;
  live_trading_enabled: boolean;
  auto_live_enabled: boolean;
  real_money_enabled: boolean;
  notes: string[];
}

interface CockpitModeErrorDetail {
  code?: string;
  message?: string;
}

function parseCockpitModeError(message: string): string {
  const marker = message.indexOf(": {");
  if (marker === -1) {
    return message;
  }

  try {
    const parsed = JSON.parse(message.slice(marker + 2).trim()) as {
      detail?: CockpitModeErrorDetail;
    };
    return parsed.detail?.message ?? message;
  } catch {
    return message;
  }
}

export async function getCockpitMode(): Promise<CockpitModeResponse> {
  return apiRequest<CockpitModeResponse>("/cockpit/mode", { method: "GET" });
}

export async function updateCockpitMode(
  requested_mode: CockpitModeId,
): Promise<CockpitModeResponse> {
  try {
    return await apiRequest<CockpitModeResponse>("/cockpit/mode", {
      method: "POST",
      body: JSON.stringify({ requested_mode }),
    });
  } catch (error) {
    if (error instanceof Error) {
      throw new Error(parseCockpitModeError(error.message));
    }
    throw error;
  }
}