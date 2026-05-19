"use client";

import { useCallback, useEffect, useMemo, useReducer, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  getPaperExecution,
  getPaperExecutionHistory,
  listPaperExecutions,
  listOpenPositions,
  type PaperExecutionHistoryResponse,
} from "../api";
import { useLivePolling } from "./useLivePolling";
import type { PaperExecutionResponse, PositionResponse } from "../types";
import { executionReducer, executionInitialState } from "../state/executionReducer";

const PAGE_SIZE = 10;
const STATUS_OPTIONS = ["", "accepted", "filled", "closed", "rejected", "canceled", "new"];

export interface ExecutionPageState {
  // List
  statusFilter: string;
  offset: number;
  list: PaperExecutionResponse[];
  isListLoading: boolean;
  listError: string | null;
  canGoPrev: boolean;
  canGoNext: boolean;
  titleStatus: string;

  // Selected execution detail
  selectedExecutionId: string | null;
  detail: PaperExecutionResponse | null;
  isDetailLoading: boolean;
  detailError: string | null;

  // History
  history: PaperExecutionHistoryResponse | null;
  isHistoryLoading: boolean;
  historyError: string | null;

  // Positions
  positions: PositionResponse[];
  isPositionsLoading: boolean;
  positionsError: string | null;
}

export interface ExecutionPageActions {
  onFilterChange: (status: string) => void;
  onSelectExecution: (id: string) => void;
  onPrevPage: () => void;
  onNextPage: () => void;
  onReloadList: () => void;
}

export function useExecutionPageController(): ExecutionPageState & ExecutionPageActions {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const urlExecutionId = searchParams.get("executionId");
  const urlAsset = searchParams.get("asset");
  const urlStatus = searchParams.get("status");
  const normalizedStatus = STATUS_OPTIONS.includes(urlStatus ?? "") ? (urlStatus ?? "") : "";

  const [exState, dispatch] = useReducer(executionReducer, {
    ...executionInitialState,
    filters: { statusFilter: normalizedStatus, offset: 0 },
  });

  const {
    filters: { statusFilter, offset },
    list,
    isListLoading,
    listError,
    selectedExecutionId,
    detail,
    isDetailLoading,
    detailError,
    history,
    isHistoryLoading,
    historyError,
  } = exState;

  const [positions, setPositions] = useState<PositionResponse[]>([]);
  const [positionsError, setPositionsError] = useState<string | null>(null);
  const [isPositionsLoading, setIsPositionsLoading] = useState(false);

  const canGoPrev = offset > 0;
  const canGoNext = list.length === PAGE_SIZE;

  const titleStatus = useMemo(() => statusFilter || "all statuses", [statusFilter]);

  const loadPositions = useCallback(async () => {
    setIsPositionsLoading(true);
    setPositionsError(null);
    try {
      setPositions(await listOpenPositions());
    } catch (error) {
      setPositions([]);
      setPositionsError(error instanceof Error ? error.message : "Failed to load positions.");
    } finally {
      setIsPositionsLoading(false);
    }
  }, []);

  // Sync URL status param → local filter
  useEffect(() => {
    if (normalizedStatus !== statusFilter) {
      dispatch({ type: "SET_FILTER", payload: { statusFilter: normalizedStatus, offset: 0 } });
    }
  }, [normalizedStatus, statusFilter]);

  const loadList = useCallback(async () => {
    dispatch({ type: "SET_LIST_LOADING", payload: true });
    dispatch({ type: "SET_LIST_ERROR", payload: null });
    try {
      const result = await listPaperExecutions({
        limit: PAGE_SIZE,
        offset,
        status: statusFilter || undefined,
      });
      dispatch({ type: "SET_LIST", payload: result });

      if (result.length === 0) {
        dispatch({ type: "SET_SELECTED", payload: null });
        dispatch({ type: "SET_DETAIL", payload: null });
        dispatch({ type: "SET_HISTORY", payload: null });
        return;
      }

      const idFromUrl =
        urlExecutionId && result.some((item) => item.execution_id === urlExecutionId)
          ? urlExecutionId
          : null;
      const currentSelection =
        selectedExecutionId && result.some((item) => item.execution_id === selectedExecutionId)
          ? selectedExecutionId
          : null;
      const assetSelection = urlAsset
        ? (result.find((item) => item.asset.toLowerCase() === urlAsset.toLowerCase())?.execution_id ?? null)
        : null;

      const nextSelection = idFromUrl ?? currentSelection ?? assetSelection ?? result[0].execution_id;
      if (nextSelection !== selectedExecutionId) {
        dispatch({ type: "SET_SELECTED", payload: nextSelection });
      }
    } catch (error) {
      dispatch({ type: "SET_LIST", payload: [] });
      dispatch({ type: "SET_SELECTED", payload: null });
      dispatch({ type: "SET_DETAIL", payload: null });
      dispatch({ type: "SET_HISTORY", payload: null });
      dispatch({ type: "SET_LIST_ERROR", payload: error instanceof Error ? error.message : "Failed to load execution list." });
    } finally {
      dispatch({ type: "SET_LIST_LOADING", payload: false });
    }
  }, [offset, selectedExecutionId, statusFilter, urlAsset, urlExecutionId]);

  // Sync filter+selection → URL
  useEffect(() => {
    const params = new URLSearchParams(searchParams.toString());
    if (statusFilter) {
      params.set("status", statusFilter);
    } else {
      params.delete("status");
    }
    if (selectedExecutionId) {
      params.set("executionId", selectedExecutionId);
      const selected = list.find((item) => item.execution_id === selectedExecutionId);
      if (selected?.asset) params.set("asset", selected.asset);
    } else {
      params.delete("executionId");
    }
    const nextQuery = params.toString();
    const currentQuery = searchParams.toString();
    if (nextQuery !== currentQuery) {
      router.replace(nextQuery ? `${pathname}?${nextQuery}` : pathname, { scroll: false });
    }
  }, [list, pathname, router, searchParams, selectedExecutionId, statusFilter]);

  // Load list on mount and when dependencies change
  useEffect(() => {
    void loadList();
  }, [loadList]);

  // Load positions whenever list changes
  useEffect(() => {
    void loadPositions();
  }, [list, loadPositions]);

  // Load detail + history when selection changes
  useEffect(() => {
    if (!selectedExecutionId) return;
    const executionId = selectedExecutionId;

    async function loadDetailAndHistory() {
      dispatch({ type: "SET_DETAIL_LOADING", payload: true });
      dispatch({ type: "SET_HISTORY_LOADING", payload: true });
      dispatch({ type: "SET_DETAIL_ERROR", payload: null });
      dispatch({ type: "SET_HISTORY_ERROR", payload: null });

      try {
        dispatch({ type: "SET_DETAIL", payload: await getPaperExecution(executionId) });
      } catch (error) {
        dispatch({ type: "SET_DETAIL", payload: null });
        dispatch({ type: "SET_DETAIL_ERROR", payload: error instanceof Error ? error.message : "Failed to load execution detail." });
      } finally {
        dispatch({ type: "SET_DETAIL_LOADING", payload: false });
      }

      try {
        dispatch({ type: "SET_HISTORY", payload: await getPaperExecutionHistory(executionId) });
      } catch (error) {
        dispatch({ type: "SET_HISTORY", payload: null });
        dispatch({ type: "SET_HISTORY_ERROR", payload: error instanceof Error ? error.message : "Failed to load execution history." });
      } finally {
        dispatch({ type: "SET_HISTORY_LOADING", payload: false });
      }
    }

    void loadDetailAndHistory();
  }, [selectedExecutionId]);

  useLivePolling(() => {
    void loadList();
    void loadPositions();
  }, 12000, { enabled: true, runImmediately: false });

  function onFilterChange(nextValue: string) {
    dispatch({ type: "SET_FILTER", payload: { statusFilter: nextValue, offset: 0 } });
  }

  function onSelectExecution(id: string) {
    dispatch({ type: "SET_SELECTED", payload: id });
  }

  function onPrevPage() {
    dispatch({ type: "SET_PAGINATION", payload: { offset: Math.max(0, offset - PAGE_SIZE) } });
  }

  function onNextPage() {
    dispatch({ type: "SET_PAGINATION", payload: { offset: offset + PAGE_SIZE } });
  }

  return {
    statusFilter,
    offset,
    list,
    isListLoading,
    listError,
    canGoPrev,
    canGoNext,
    titleStatus,
    selectedExecutionId,
    detail,
    isDetailLoading,
    detailError,
    history,
    isHistoryLoading,
    historyError,
    positions,
    isPositionsLoading,
    positionsError,
    onFilterChange,
    onSelectExecution,
    onPrevPage,
    onNextPage,
    onReloadList: () => { void loadList(); },
  };
}
