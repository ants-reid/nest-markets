"use client";

interface JsonCardProps {
  title: string;
  data: unknown | null;
  emptyText?: string;
}

export function JsonCard({ title, data, emptyText = "No response yet." }: JsonCardProps) {
  return (
    <section
      style={{
        display: "grid",
        gap: 10,
        padding: 22,
        borderRadius: 20,
        border: "1px solid var(--surface-border)",
        background: "var(--surface-fill)",
        boxShadow: "var(--surface-shadow)",
      }}
    >
      <h2 style={{ margin: 0, color: "var(--text-strong)", fontSize: 22 }}>{title}</h2>
      {data === null ? (
        <p style={{ margin: 0, color: "var(--text-muted)" }}>{emptyText}</p>
      ) : (
        <pre
          style={{
            margin: 0,
            padding: 14,
            borderRadius: 12,
            border: "1px solid var(--surface-border)",
            background: "var(--surface-soft)",
            color: "var(--text-body)",
            fontSize: 13,
            lineHeight: 1.5,
            overflowX: "auto",
          }}
        >
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </section>
  );
}
