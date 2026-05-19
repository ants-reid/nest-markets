import styles from "./StatusChip.module.css";

export type StatusVariant = "success" | "warning" | "danger" | "info" | "muted" | "accent";
export type StatusSize = "sm" | "md" | "lg";

interface StatusChipProps {
  variant?: StatusVariant;
  size?: StatusSize;
  label: string;
  dot?: boolean;
  className?: string;
}

/**
 * Derive a variant from a common execution/trade status string.
 * Falls back to "muted" for unknown values.
 */
export function statusVariantFor(status: string): StatusVariant {
  switch (status.toLowerCase()) {
    case "filled":
    case "active":
    case "live":
    case "ok":
    case "passing":
      return "success";
    case "accepted":
    case "submitted":
    case "info":
      return "info";
    case "new":
    case "queued":
    case "pending":
      return "accent";
    case "closed":
    case "completed":
    case "done":
      return "muted";
    case "rejected":
    case "failed":
    case "error":
    case "down":
      return "danger";
    case "canceled":
    case "cancelled":
    case "warning":
    case "expired":
      return "warning";
    default:
      return "muted";
  }
}

export function StatusChip({ variant = "muted", size = "md", label, dot = true, className }: StatusChipProps) {
  const cls = [
    styles.chip,
    styles[variant],
    size !== "md" ? styles[size] : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <span className={cls}>
      {dot && <span className={styles.dot} aria-hidden="true" />}
      {label}
    </span>
  );
}
