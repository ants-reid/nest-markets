"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import {
  listAlertNotifications,
  markAlertNotificationRead,
  type AlertNotificationResponse,
} from "../lib/api";

interface OperatorNotificationSurfaceProps {
  title?: string;
  maxItems?: number;
}

type NotificationState =
  | { state: "loading"; data: null; error: null }
  | { state: "ready"; data: AlertNotificationResponse[]; error: null }
  | { state: "error"; data: null; error: string };

function panelStyle(): React.CSSProperties {
  return {
    display: "grid",
    gap: 14,
    padding: 22,
    borderRadius: 20,
    background: "var(--surface-fill)",
    border: "1px solid var(--surface-border)",
    boxShadow: "var(--surface-shadow)",
  };
}

function unreadBadgeStyle(unreadCount: number): React.CSSProperties {
  return {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    minWidth: 30,
    padding: "4px 10px",
    borderRadius: 999,
    fontSize: 12,
    fontWeight: 800,
    letterSpacing: 0.4,
    color: unreadCount > 0 ? "var(--state-danger)" : "var(--text-muted)",
    background: unreadCount > 0 ? "var(--state-danger-soft)" : "color-mix(in oklab, var(--text-muted) 14%, transparent)",
    border: `1px solid ${unreadCount > 0 ? "var(--state-danger-border)" : "var(--control-border)"}`,
  };
}

function levelBadgeStyle(level: string): React.CSSProperties {
  const warning = level.toLowerCase() === "warning";
  return {
    display: "inline-block",
    borderRadius: 999,
    padding: "3px 10px",
    fontSize: 11,
    fontWeight: 700,
    textTransform: "uppercase",
    letterSpacing: 0.7,
    background: warning ? "var(--state-danger-soft)" : "var(--state-success-soft)",
    color: warning ? "var(--state-danger)" : "var(--state-success)",
    border: `1px solid ${warning ? "var(--state-danger-border)" : "var(--state-success-border)"}`,
  };
}

export function OperatorNotificationSurface({
  title = "Operator Notifications",
  maxItems = 4,
}: OperatorNotificationSurfaceProps) {
  const [notifications, setNotifications] = useState<NotificationState>({ state: "loading", data: null, error: null });
  const [actionId, setActionId] = useState<string | null>(null);

  async function loadNotifications() {
    setNotifications({ state: "loading", data: null, error: null });
    try {
      const data = await listAlertNotifications();
      setNotifications({ state: "ready", data, error: null });
    } catch (err) {
      setNotifications({
        state: "error",
        data: null,
        error: err instanceof Error ? err.message : "Failed to load notifications.",
      });
    }
  }

  useEffect(() => {
    void loadNotifications();
  }, []);

  const allItems = useMemo(() => (notifications.state === "ready" ? notifications.data : []), [notifications]);
  const unreadCount = useMemo(() => allItems.filter((item) => !item.is_read).length, [allItems]);
  const recentItems = useMemo(() => allItems.slice(0, maxItems), [allItems, maxItems]);

  async function markRead(notificationId: string) {
    setActionId(notificationId);
    try {
      await markAlertNotificationRead(notificationId);
      await loadNotifications();
    } finally {
      setActionId(null);
    }
  }

  return (
    <section style={panelStyle()}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <h2 style={{ margin: 0, color: "var(--text-strong)", fontSize: 24, letterSpacing: 0.2 }}>{title}</h2>
        <span style={unreadBadgeStyle(unreadCount)}>Unread: {unreadCount}</span>
      </div>

      <p style={{ margin: 0, color: "var(--text-muted)", fontSize: 13, lineHeight: 1.55 }}>
        Recent alert notifications with quick read actions and deep links for execution triage.
      </p>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button
          type="button"
          onClick={() => {
            void loadNotifications();
          }}
          style={{
            border: "1px solid var(--state-info-border)",
            borderRadius: 999,
            background: "var(--surface-soft)",
            color: "var(--text-strong)",
            padding: "7px 13px",
            fontWeight: 700,
            cursor: "pointer",
            fontSize: 12,
          }}
        >
          Refresh
        </button>
        <Link
          href="/alerts"
          style={{
            border: "1px solid var(--surface-border)",
            borderRadius: 999,
            background: "var(--surface-soft)",
            color: "var(--text-muted)",
            padding: "6px 13px",
            fontWeight: 700,
            cursor: "pointer",
            fontSize: 12,
            textDecoration: "none",
          }}
        >
          Open Alerts
        </Link>
      </div>

      {notifications.state === "loading" ? <p style={{ margin: 0, color: "var(--text-muted)" }}>Loading notifications...</p> : null}

      {notifications.state === "error" ? (
        <div
          style={{
            padding: 12,
            borderRadius: 10,
            border: "1px solid var(--state-danger-border)",
            background: "var(--state-danger-soft)",
            color: "var(--state-danger)",
          }}
        >
          {notifications.error}
        </div>
      ) : null}

      {notifications.state === "ready" && recentItems.length === 0 ? (
        <div
          style={{
            padding: 14,
            borderRadius: 12,
            border: "1px dashed var(--surface-border)",
            color: "var(--text-muted)",
            background: "var(--surface-soft)",
          }}
        >
          No recent notifications. Add or match an alert rule to generate operator notifications.
        </div>
      ) : null}

      {notifications.state === "ready" && recentItems.length > 0 ? (
        <div style={{ display: "grid", gap: 10 }}>
          {recentItems.map((notification) => (
            <div
              key={notification.notification_id}
              style={{
                display: "grid",
                gridTemplateColumns: "auto 1fr auto auto",
                gap: 12,
                padding: "12px 14px",
                borderRadius: 12,
                border: `1px solid ${notification.level === "warning" ? "var(--state-danger-border)" : "var(--surface-border)"}`,
                background: notification.level === "warning" ? "var(--state-danger-soft)" : "var(--state-success-soft)",
                alignItems: "center",
              }}
            >
              <span style={levelBadgeStyle(notification.is_read ? "info" : "warning")}>
                {notification.is_read ? "read" : "unread"}
              </span>

              <div style={{ display: "grid", gap: 6 }}>
                <span style={{ fontSize: 12, color: "var(--text-body)" }}>{notification.message}</span>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <Link
                    href={`/execution?asset=${encodeURIComponent(notification.asset)}&executionId=${encodeURIComponent(notification.execution_id)}&status=${encodeURIComponent(notification.status)}`}
                    style={{
                      fontSize: 11,
                      color: "var(--state-success)",
                      fontWeight: 700,
                      textDecoration: "none",
                      border: "1px solid var(--state-success-border)",
                      borderRadius: 6,
                      padding: "3px 7px",
                    }}
                  >
                    Execution
                  </Link>
                  <Link
                    href={`/workflow?asset=${encodeURIComponent(notification.asset)}&executionId=${encodeURIComponent(notification.execution_id)}&status=${encodeURIComponent(notification.status)}`}
                    style={{
                      fontSize: 11,
                      color: "var(--state-success)",
                      fontWeight: 700,
                      textDecoration: "none",
                      border: "1px solid var(--state-success-border)",
                      borderRadius: 6,
                      padding: "3px 7px",
                    }}
                  >
                    Workflow
                  </Link>
                </div>
              </div>

              <span style={levelBadgeStyle(notification.level)}>{notification.level}</span>

              <button
                type="button"
                onClick={() => {
                  void markRead(notification.notification_id);
                }}
                disabled={notification.is_read || actionId !== null}
                style={{
                  alignItems: "center",
                  border: "1px solid var(--surface-border)",
                  borderRadius: 8,
                  background: "var(--surface-soft)",
                  color: "var(--text-muted)",
                  display: "inline-flex",
                  fontWeight: 700,
                  justifyContent: "center",
                  minHeight: 32,
                  padding: "6px 10px",
                  cursor: notification.is_read || actionId !== null ? "not-allowed" : "pointer",
                  fontSize: 11,
                  lineHeight: 1.2,
                }}
              >
                {actionId === notification.notification_id ? "Marking..." : "Mark read"}
              </button>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}