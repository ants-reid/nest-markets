import { apiRequest, VISUAL_SEED_PREVIEW_ENABLED } from "./core";

export interface AlertRuleResponse {
  rule_id: string;
  asset: string;
  condition: string;
  status: string;
  created_at: string;
  updated_at: string;
  snoozed_until: string | null;
}

export interface ActiveAlertResponse {
  alert_id: string;
  rule_id: string;
  execution_id: string;
  asset: string;
  status: string;
  message: string;
  level: string;
}

export interface AlertNotificationResponse {
  notification_id: string;
  alert_id: string;
  rule_id: string;
  execution_id: string;
  asset: string;
  status: string;
  message: string;
  level: string;
  is_read: boolean;
  read_at: string | null;
}

export async function createAlertRule(payload: {
  asset: string;
  condition: string;
}): Promise<AlertRuleResponse> {
  return apiRequest<AlertRuleResponse>("/approvals/alerts/rules", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listAlertRules(): Promise<AlertRuleResponse[]> {
  return apiRequest<AlertRuleResponse[]>("/approvals/alerts/rules", { method: "GET" });
}

export async function listActiveAlerts(): Promise<ActiveAlertResponse[]> {
  const path = VISUAL_SEED_PREVIEW_ENABLED
    ? "/approvals/alerts/active?include_visual_seed=true"
    : "/approvals/alerts/active";
  return apiRequest<ActiveAlertResponse[]>(path, { method: "GET" });
}

export async function acknowledgeAlertRule(ruleId: string): Promise<AlertRuleResponse> {
  return apiRequest<AlertRuleResponse>(`/approvals/alerts/rules/${ruleId}/acknowledge`, { method: "POST" });
}

export async function snoozeAlertRule(ruleId: string, minutes: number): Promise<AlertRuleResponse> {
  return apiRequest<AlertRuleResponse>(`/approvals/alerts/rules/${ruleId}/snooze`, {
    method: "POST",
    body: JSON.stringify({ minutes }),
  });
}

export async function listAlertNotifications(): Promise<AlertNotificationResponse[]> {
  const path = VISUAL_SEED_PREVIEW_ENABLED
    ? "/approvals/alerts/notifications?include_visual_seed=true"
    : "/approvals/alerts/notifications";
  return apiRequest<AlertNotificationResponse[]>(path, { method: "GET" });
}

export async function markAlertNotificationRead(notificationId: string): Promise<AlertNotificationResponse> {
  const path = VISUAL_SEED_PREVIEW_ENABLED
    ? `/approvals/alerts/notifications/${notificationId}/read?include_visual_seed=true`
    : `/approvals/alerts/notifications/${notificationId}/read`;
  return apiRequest<AlertNotificationResponse>(path, {
    method: "POST",
  });
}
