import styles from "./PageShell.module.css";

type PageWidth = "md" | "lg" | "xl" | "full";

interface PageShellProps {
  children: React.ReactNode;
  width?: PageWidth;
  className?: string;
}

export function PageShell({ children, width = "lg", className }: PageShellProps) {
  return (
    <main className={styles.shell}>
      <div className={[styles.inner, styles[width], className].filter(Boolean).join(" ")}>
        {children}
      </div>
    </main>
  );
}
