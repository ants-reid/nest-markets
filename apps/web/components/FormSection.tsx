"use client";

import type { ReactNode } from "react";

interface FormSectionProps {
  title: string;
  description: string;
  children: ReactNode;
}

export function FormSection({ title, description, children }: FormSectionProps) {
  return (
    <section
      style={{
        display: "grid",
        gap: 14,
        padding: 22,
        borderRadius: 20,
        border: "1px solid var(--surface-border)",
        background: "var(--surface-fill)",
        boxShadow: "var(--surface-shadow)",
      }}
    >
      <div style={{ display: "grid", gap: 6 }}>
        <h2 style={{ margin: 0, color: "var(--text-strong)", fontSize: 24 }}>{title}</h2>
        <p style={{ margin: 0, color: "var(--text-muted)", lineHeight: 1.55 }}>{description}</p>
      </div>
      {children}
    </section>
  );
}
