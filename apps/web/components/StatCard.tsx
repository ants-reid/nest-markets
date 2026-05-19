"use client";

import Link from "next/link";

interface StatCardProps {
  title: string;
  value: string;
  description: string;
  href?: string;
}

export function StatCard({ title, value, description, href }: StatCardProps) {
  const content = (
    <article
      style={{
        display: "grid",
        gap: 10,
        minHeight: 150,
        padding: 22,
        borderRadius: 20,
        border: "1px solid var(--surface-border)",
        background: "var(--surface-fill)",
        boxShadow: "var(--surface-shadow)",
      }}
    >
      <span style={{ color: "var(--text-muted)", fontSize: 11, textTransform: "uppercase", letterSpacing: 1.4, fontWeight: 700 }}>
        {title}
      </span>
      <strong style={{ color: "var(--accent-highlight)", fontSize: 34, lineHeight: 1.05, letterSpacing: 0.2, fontVariantNumeric: "tabular-nums" }}>{value}</strong>
      <p style={{ margin: 0, color: "var(--text-muted)", lineHeight: 1.5, fontSize: 13 }}>{description}</p>
    </article>
  );

  if (!href) {
    return content;
  }

  return (
    <Link href={href} style={{ textDecoration: "none" }}>
      {content}
    </Link>
  );
}