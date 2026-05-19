import Link from "next/link";
import { Badge } from "./Badge";
import { Card } from "./Card";
import styles from "./MetricCard.module.css";

interface MetricCardProps {
  title: string;
  value: string;
  description: string;
  href?: string;
  trend?: "up" | "down" | "neutral";
}

export function MetricCard({ title, value, description, href, trend }: MetricCardProps) {
  const trendVariant =
    trend === "up" ? "success" : trend === "down" ? "danger" : trend === "neutral" ? "default" : undefined;

  const content = (
    <Card className={styles.metricCard}>
      <span className={styles.title}>{title}</span>
      <div className={styles.valueRow}>
        <strong className={styles.value}>{value}</strong>
        {trendVariant && (
          <Badge variant={trendVariant}>
            {trend === "up" ? "↑" : trend === "down" ? "↓" : "—"}
          </Badge>
        )}
      </div>
      <p className={styles.description}>{description}</p>
    </Card>
  );

  if (!href) return content;

  return (
    <Link href={href} className={styles.link}>
      {content}
    </Link>
  );
}
