import { MetricCard } from "../ui/MetricCard";
import styles from "./DashboardMetricsSection.module.css";

interface MetricsData {
  openPositions: { length: number };
  unreadNotifications: number;
  openNotional: number;
  activeAlerts: number;
  ruleCount: number;
  statusCounts: { pending: number };
  totalExecutions: number;
}

interface DashboardMetricsSectionProps {
  metrics: MetricsData;
  formatMoney: (value: number) => string;
}

export function DashboardMetricsSection({ metrics, formatMoney }: DashboardMetricsSectionProps) {
  const cards = [
    { label: "Open positions", value: String(metrics.openPositions.length), hint: "currently active", href: "/execution", trend: "neutral" as const },
    { label: "Unread notifications", value: String(metrics.unreadNotifications), hint: "from alert stream", href: "/notifications", trend: metrics.unreadNotifications > 0 ? "down" as const : "neutral" as const },
    { label: "Open notional", value: formatMoney(metrics.openNotional), hint: "live exposure proxy", href: "/execution", trend: metrics.openNotional > 0 ? "up" as const : "neutral" as const },
    { label: "Active alerts", value: String(metrics.activeAlerts), hint: `${metrics.ruleCount} total rules`, href: "/alerts", trend: metrics.activeAlerts > 0 ? "up" as const : "neutral" as const },
    { label: "Pending workflow", value: String(metrics.statusCounts.pending), hint: "new/submitted/rejected", href: "/workflow", trend: metrics.statusCounts.pending > 0 ? "up" as const : "neutral" as const },
    { label: "Execution activity", value: String(metrics.totalExecutions), hint: "records available", href: "/analytics", trend: metrics.totalExecutions > 0 ? "up" as const : "neutral" as const },
  ];

  return (
    <section className={styles.grid}>
      {cards.map((card) => (
        <MetricCard
          key={card.label}
          title={card.label}
          value={card.value}
          description={card.hint}
          href={card.href}
          trend={card.trend}
        />
      ))}
    </section>
  );
}
