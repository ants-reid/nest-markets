import type {
  LiveExecutionRequest,
  LiveExecutionResponse,
  PaperExecutionRequest,
  PaperExecutionResponse,
  PositionResponse,
} from "../types";
import { apiRequest, journalSubscribers, notifyJournalSubscribers, VISUAL_SEED_PREVIEW_ENABLED, type ExecutionJournalSubscriber } from "./core";

export interface ListPaperExecutionsParams {
  limit?: number;
  offset?: number;
  status?: string;
}

export interface PaperExecutionHistoryResponse {
  execution_id: string;
  events: string[];
}

export interface WorkerResultResponse {
  worker_name: string;
  status: string;
  message: string;
  started_at: string;
  finished_at: string;
}

export type JournalOutcomeTag =
  | "untagged"
  | "worked"
  | "partial"
  | "stopped_out"
  | "expired"
  | "invalidated";

export interface ExecutionJournalEntry {
  executionId: string;
  asset?: string;
  status?: string;
  note: string;
  tags: string[];
  outcomeTag: JournalOutcomeTag;
  updatedAt: string;
}

interface BackendExecutionJournalEntry {
  execution_id: string;
  outcome_tag: JournalOutcomeTag;
  note: string;
  tags: string[];
  updated_at: string;
}

function normalizeExecutionJournalEntry(
  journal: BackendExecutionJournalEntry,
  context?: { asset?: string; status?: string },
): ExecutionJournalEntry {
  return {
    executionId: journal.execution_id,
    asset: context?.asset,
    status: context?.status,
    note: journal.note,
    tags: journal.tags,
    outcomeTag: journal.outcome_tag,
    updatedAt: journal.updated_at,
  };
}

export async function submitPaperExecution(payload: PaperExecutionRequest): Promise<PaperExecutionResponse> {
  return apiRequest<PaperExecutionResponse>("/execution/paper", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function submitLiveExecution(payload: LiveExecutionRequest): Promise<LiveExecutionResponse> {
  return apiRequest<LiveExecutionResponse>("/execution/live", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listPaperExecutions(
  params: ListPaperExecutionsParams = {},
): Promise<PaperExecutionResponse[]> {
  const search = new URLSearchParams();
  if (typeof params.limit === "number") search.set("limit", String(params.limit));
  if (typeof params.offset === "number") search.set("offset", String(params.offset));
  if (params.status) search.set("status", params.status);
  if (VISUAL_SEED_PREVIEW_ENABLED) search.set("include_visual_seed", "true");
  const query = search.toString();
  const path = query ? `/execution/paper?${query}` : "/execution/paper";
  return apiRequest<PaperExecutionResponse[]>(path, { method: "GET" });
}

export async function getPaperExecution(executionId: string): Promise<PaperExecutionResponse> {
  return apiRequest<PaperExecutionResponse>(`/execution/paper/${executionId}`, { method: "GET" });
}

export async function getPaperExecutionHistory(executionId: string): Promise<PaperExecutionHistoryResponse> {
  return apiRequest<PaperExecutionHistoryResponse>(`/execution/paper/${executionId}/history`, {
    method: "GET",
  });
}

export async function listOpenPositions(): Promise<PositionResponse[]> {
  const path = VISUAL_SEED_PREVIEW_ENABLED
    ? "/execution/positions?include_visual_seed=true"
    : "/execution/positions";
  return apiRequest<PositionResponse[]>(path, { method: "GET" });
}

export async function runAutoPaperTrader(source: "manual" | "scheduled" = "manual"): Promise<WorkerResultResponse> {
  return apiRequest<WorkerResultResponse>(`/market-data/auto-paper/run?source=${source}`, {
    method: "POST",
  });
}

export interface RunHistoryEntry {
  worker_name: string;
  status: string;
  message: string;
  started_at: string;
  finished_at: string;
  source: string;
}

export async function getAutoPaperHistory(limit = 20): Promise<RunHistoryEntry[]> {
  return apiRequest<RunHistoryEntry[]>(`/market-data/auto-paper/history?limit=${limit}`, { method: "GET" });
}

export interface SchedulerJobStatus {
  job_id: string;
  next_run_time: string | null;
  state: "running" | "paused" | "missing" | "scheduler_unavailable";
}

export async function getSchedulerStatus(): Promise<SchedulerJobStatus> {
  return apiRequest<SchedulerJobStatus>("/market-data/auto-paper/scheduler/status", { method: "GET" });
}

export async function pauseScheduler(): Promise<SchedulerJobStatus> {
  return apiRequest<SchedulerJobStatus>("/market-data/auto-paper/scheduler/pause", { method: "POST" });
}

export async function resumeScheduler(): Promise<SchedulerJobStatus> {
  return apiRequest<SchedulerJobStatus>("/market-data/auto-paper/scheduler/resume", { method: "POST" });
}

export interface KillSwitchResponse {
  kill_switch_active: boolean;
  profile_name: string | null;
  profile_is_active: string | null;
}

export async function getKillSwitch(): Promise<KillSwitchResponse> {
  return apiRequest<KillSwitchResponse>("/market-data/auto-paper/kill-switch", { method: "GET" });
}

export async function activateKillSwitch(): Promise<KillSwitchResponse> {
  return apiRequest<KillSwitchResponse>("/market-data/auto-paper/kill-switch/activate", { method: "POST" });
}

export async function deactivateKillSwitch(): Promise<KillSwitchResponse> {
  return apiRequest<KillSwitchResponse>("/market-data/auto-paper/kill-switch/deactivate", { method: "POST" });
}

export async function getExecutionJournalEntry(
  executionId: string,
  context?: { asset?: string; status?: string },
): Promise<ExecutionJournalEntry | null> {
  try {
    const response = await apiRequest<BackendExecutionJournalEntry>(`/execution/paper/${executionId}/journal`, {
      method: "GET",
    });
    return normalizeExecutionJournalEntry(response, context);
  } catch (error) {
    if (error instanceof Error && error.message.includes("404")) return null;
    throw error;
  }
}

export async function getExecutionJournalEntries(
  executions: Array<{ execution_id: string; asset?: string; status?: string }>,
): Promise<ExecutionJournalEntry[]> {
  const settled = await Promise.all(
    executions.map(async (execution) => {
      try {
        return await getExecutionJournalEntry(execution.execution_id, {
          asset: execution.asset,
          status: execution.status,
        });
      } catch {
        return null;
      }
    }),
  );
  return settled
    .filter((entry): entry is ExecutionJournalEntry => entry !== null)
    .sort((a, b) => Date.parse(b.updatedAt) - Date.parse(a.updatedAt));
}

export async function saveExecutionJournalEntry(input: {
  executionId: string;
  asset?: string;
  status?: string;
  note: string;
  tags: string[];
  outcomeTag: JournalOutcomeTag;
}): Promise<ExecutionJournalEntry> {
  const response = await apiRequest<BackendExecutionJournalEntry>(`/execution/paper/${input.executionId}/journal`, {
    method: "PUT",
    body: JSON.stringify({
      outcome_tag: input.outcomeTag,
      note: input.note.trim(),
      tags: input.tags.map((tag) => tag.trim().toLowerCase()).filter(Boolean),
    }),
  });
  const entry = normalizeExecutionJournalEntry(response, {
    asset: input.asset,
    status: input.status,
  });
  notifyJournalSubscribers();
  return entry;
}

export function subscribeExecutionJournal(subscriber: ExecutionJournalSubscriber): () => void {
  journalSubscribers.add(subscriber);
  return () => {
    journalSubscribers.delete(subscriber);
  };
}
