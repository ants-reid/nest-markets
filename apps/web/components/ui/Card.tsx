"use client";

import styles from "./Card.module.css";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  interactive?: boolean;
}

export function Card({ children, className, interactive = false }: CardProps) {
  const classes = [styles.card, interactive ? styles.interactive : "", className]
    .filter(Boolean)
    .join(" ");

  return <div className={classes}>{children}</div>;
}
