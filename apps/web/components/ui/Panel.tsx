import { Card } from "./Card";
import styles from "./Panel.module.css";

interface PanelProps {
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  controls?: React.ReactNode;
  legend?: React.ReactNode;
  children: React.ReactNode;
  contentGap?: number;
  className?: string;
}

export function Panel({ title, subtitle, controls, legend, children, contentGap = 12, className }: PanelProps) {
  const hasHeader = title || controls;

  return (
    <Card className={[styles.panel, className].filter(Boolean).join(" ")}>
      {hasHeader && (
        <div className={styles.header}>
          <div className={styles.titleGroup}>
            {title && <div className={styles.title}>{title}</div>}
            {subtitle && <div className={styles.subtitle}>{subtitle}</div>}
          </div>
          {controls && <div className={styles.controls}>{controls}</div>}
        </div>
      )}
      {legend && <div className={styles.legend}>{legend}</div>}
      <div className={styles.content} style={{ "--panel-content-gap": `${contentGap}px` } as React.CSSProperties}>
        {children}
      </div>
    </Card>
  );
}
