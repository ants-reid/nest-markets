import Link from "next/link";
import styles from "./DashboardAlertsSection.module.css";

interface AttentionItem {
  text: string;
  tone: string;
  href: string;
}

interface DashboardAlertsSectionProps {
  attentionItems: AttentionItem[];
  onRefresh: () => void;
}

export function DashboardAlertsSection({ attentionItems, onRefresh }: DashboardAlertsSectionProps) {
  return (
    <section className={styles.panel}>
      <div className={styles.header}>
        <div className={styles.headerText}>
          <span className={styles.eyebrow}>Personal Operator Cockpit</span>
          <h1 data-rs="hero-title" className={styles.title}>What Needs Attention Now</h1>
          <p className={styles.subtitle}>
            Main dashboard is focused on your live operating lane: positions, alerts, approvals/workflow queue,
            risk pressure, unread notifications, and immediate next actions.
          </p>
        </div>
        <button type="button" className={styles.refreshButton} onClick={onRefresh}>
          Refresh cockpit
        </button>
      </div>

      <div className={styles.itemList}>
        {attentionItems.map((item) => (
          <Link
            key={item.text}
            href={item.href}
            className={styles.attentionItem}
          >
            <span className={styles.itemText}>{item.text}</span>
            <span className={styles.itemAction} style={{ color: item.tone }}>
              review
            </span>
          </Link>
        ))}
      </div>
    </section>
  );
}
