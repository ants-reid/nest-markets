import type { PaperExecutionResponse } from "../types";
import type { PaperExecutionHistoryResponse } from "../api";

export interface ExecutionFilters {
  statusFilter: string;
  offset: number;
}

export interface ExecutionState {
  filters: ExecutionFilters;
  list: PaperExecutionResponse[];
  isListLoading: boolean;
  listError: string | null;
  selectedExecutionId: string | null;
  detail: PaperExecutionResponse | null;
  isDetailLoading: boolean;
  detailError: string | null;
  history: PaperExecutionHistoryResponse | null;
  isHistoryLoading: boolean;
  historyError: string | null;
}

export type ExecutionAction =
  | { type: "SET_FILTER"; payload: Partial<ExecutionFilters> }
  | { type: "SET_LIST_LOADING"; payload: boolean }
  | { type: "SET_LIST"; payload: PaperExecutionResponse[] }
  | { type: "SET_LIST_ERROR"; payload: string | null }
  | { type: "SET_DETAIL"; payload: PaperExecutionResponse | null }
  | { type: "SET_DETAIL_LOADING"; payload: boolean }
  | { type: "SET_DETAIL_ERROR"; payload: string | null }
  | { type: "SET_HISTORY"; payload: PaperExecutionHistoryResponse | null }
  | { type: "SET_HISTORY_LOADING"; payload: boolean }
  | { type: "SET_HISTORY_ERROR"; payload: string | null }
  | { type: "SET_SELECTED"; payload: string | null }
  | { type: "SET_PAGINATION"; payload: { offset: number } }
  | { type: "RESET" };

export const executionInitialState: ExecutionState = {
  filters: {
    statusFilter: "",
    offset: 0,
  },
  list: [],
  isListLoading: false,
  listError: null,
  selectedExecutionId: null,
  detail: null,
  isDetailLoading: false,
  detailError: null,
  history: null,
  isHistoryLoading: false,
  historyError: null,
};

export function executionReducer(state: ExecutionState, action: ExecutionAction): ExecutionState {
  switch (action.type) {
    case "SET_FILTER":
      return { ...state, filters: { ...state.filters, ...action.payload } };
    case "SET_LIST_LOADING":
      return { ...state, isListLoading: action.payload };
    case "SET_LIST":
      return { ...state, list: action.payload };
    case "SET_LIST_ERROR":
      return { ...state, listError: action.payload };
    case "SET_DETAIL":
      return { ...state, detail: action.payload };
    case "SET_DETAIL_LOADING":
      return { ...state, isDetailLoading: action.payload };
    case "SET_DETAIL_ERROR":
      return { ...state, detailError: action.payload };
    case "SET_HISTORY":
      return { ...state, history: action.payload };
    case "SET_HISTORY_LOADING":
      return { ...state, isHistoryLoading: action.payload };
    case "SET_HISTORY_ERROR":
      return { ...state, historyError: action.payload };
    case "SET_SELECTED":
      return { ...state, selectedExecutionId: action.payload };
    case "SET_PAGINATION":
      return { ...state, filters: { ...state.filters, offset: action.payload.offset } };
    case "RESET":
      return executionInitialState;
    default:
      return state;
  }
}
