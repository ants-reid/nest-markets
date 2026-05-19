import styles from "./Badge.module.css";

type BadgeVariant = "default" | "success" | "warning" | "danger" | "info";

interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  icon?: React.ReactNode;
}

export function Badge({ variant = "default", children, icon }: BadgeProps) {
  return (
    <span className={[styles.badge, styles[variant]].join(" ")}>
      {icon && <span className={styles.icon}>{icon}</span>}
      {children}
    </span>
  );
}
