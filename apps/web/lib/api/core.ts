export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

const explicitPreview = process.env.NEXT_PUBLIC_VISUAL_SEED_PREVIEW;
export const VISUAL_SEED_PREVIEW_ENABLED = explicitPreview
  ? explicitPreview.toLowerCase() === "true"
  : process.env.NODE_ENV !== "production";

export type ExecutionJournalSubscriber = () => void;

export const journalSubscribers = new Set<ExecutionJournalSubscriber>();

export function notifyJournalSubscribers() {
  for (const subscriber of journalSubscribers) {
    subscriber();
  }
}

export async function apiRequest<TResponse>(path: string, init: RequestInit): Promise<TResponse> {
  const headers = new Headers(init.headers ?? undefined);
  const hasBody = init.body !== undefined && init.body !== null;

  if (hasBody && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
    ...init,
    headers,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(`API request failed with status ${response.status}${message ? `: ${message}` : ""}`);
  }

  return (await response.json()) as TResponse;
}
