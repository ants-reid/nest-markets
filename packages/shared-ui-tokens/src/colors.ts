/** Brand & neutral palette tokens (map to CSS vars in globals.css) */
export const colors = {
  // Brand
  brandPrimary: "var(--brand-primary)",
  brandAccent: "var(--brand-accent)",
  brandMuted: "var(--brand-muted)",

  // Backgrounds
  appShellBg: "var(--app-shell-bg)",
  sidebarBg: "var(--sidebar-bg)",
  surfaceFill: "var(--surface-fill)",
  surfaceSubtle: "var(--surface-subtle)",
  cardBg: "var(--card-bg)",
  panelBg: "var(--panel-bg)",

  // Text
  textPrimary: "var(--text-primary)",
  textSecondary: "var(--text-secondary)",
  textMuted: "var(--text-muted)",
  textInverse: "var(--text-inverse)",

  // State
  stateSuccess: "var(--state-success)",
  stateWarning: "var(--state-warning)",
  stateDanger: "var(--state-danger)",
  stateInfo: "var(--state-info)",

  // Border
  borderDefault: "var(--border-default)",
  borderSubtle: "var(--border-subtle)",
} as const;

export type ColorToken = keyof typeof colors;
