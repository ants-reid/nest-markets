import styles from "./EmptyState.module.css";

interface EmptyStateProps {
  variant?: "empty" | "loading" | "error";
  icon?: React.ReactNode;
  title?: string;
  message?: string;
  action?: React.ReactNode;
  inline?: boolean;
  className?: string;
}

const DEFAULT_ICONS: Record<string, string> = {
  empty: "○",
  loading: "",
  error: "⚠",
};

const DEFAULT_TITLES: Record<string, string> = {
  empty: "No data",
  loading: "Loading…",
  error: "Something went wrong",
};

export function EmptyState({
  variant = "empty",
  icon,
  title,
  message,
  action,
  inline = false,
  className,
}: EmptyStateProps) {
  const cls = [
    styles.wrap,
    variant === "error" ? styles.errorWrap : "",
    inline ? styles.inline : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={cls} role={variant === "error" ? "alert" : undefined}>
      {variant === "loading" && !icon ? (
        <div className={styles.spinner} aria-label="Loading" role="status" />
      ) : (
        <span className={styles.icon} aria-hidden="true">
          {icon ?? DEFAULT_ICONS[variant]}
        </span>
      )}
      <p className={styles.title}>{title ?? DEFAULT_TITLES[variant]}</p>
      {message && <p className={styles.message}>{message}</p>}
      {action && <div className={styles.action}>{action}</div>}
    </div>
  );
}
