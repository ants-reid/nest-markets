"use client";

interface NewsItem {
  id: string;
  headline: string;
  source: string;
  published_at: string;
  sentiment: string | null;
  symbols: string[];
}

interface Props {
  items: NewsItem[];
}

export function NewsIntelligence({ items }: Props) {
  if (items.length === 0) {
    return (
      <p className="text-muted-foreground text-sm">No news items loaded.</p>
    );
  }

  return (
    <ul className="space-y-2">
      {items.map((n) => (
        <li key={n.id} className="border rounded p-3">
          <p className="text-sm font-medium">{n.headline}</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            {n.source} · {n.published_at.slice(0, 10)}
            {n.symbols.length > 0 && ` · ${n.symbols.join(", ")}`}
          </p>
        </li>
      ))}
    </ul>
  );
}
