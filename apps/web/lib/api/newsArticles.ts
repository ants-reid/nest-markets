// MH-NEWS-07-B — News-archive API client (read-only).

import { apiRequest } from "./core";

export interface NewsCitation {
  title?: string;
  url?: string;
  source?: string;
  [key: string]: unknown;
}

export interface NewsArticleItem {
  id: string;
  created_at: string | null;
  published_at: string | null;
  headline: string | null;
  summary: string | null;
  body_text: string | null;
  source_name: string | null;
  url: string | null;
  provider_article_id: string | null;
  sentiment_provider: string | null;
  evidence_class: string;
  tickers: string[] | null;
  sector_tags: string[] | null;
  citations: NewsCitation[] | null;
  authors: string[] | null;
}

export interface NewsArticlesResponse {
  count: number;
  limit: number;
  filters: {
    source: string | null;
    ticker: string | null;
  };
  items: NewsArticleItem[];
}

export interface NewsArticlesQuery {
  limit?: number;
  source?: string;
  ticker?: string;
}

export async function getRecentNewsArticles(
  query: NewsArticlesQuery = {},
): Promise<NewsArticlesResponse> {
  const params = new URLSearchParams();
  if (query.limit !== undefined) params.set("limit", String(query.limit));
  if (query.source) params.set("source", query.source);
  if (query.ticker) params.set("ticker", query.ticker);
  const qs = params.toString();
  const path = qs ? `/news-articles/recent?${qs}` : "/news-articles/recent";
  return apiRequest<NewsArticlesResponse>(path, { method: "GET" });
}
