import { apiRequest } from "./core";
import type {
  DataQualityOutliersResponse,
  DataQualityReviewRequest,
  DataQualityReviewResponse,
  DataQualityAuditResponse,
  DataQualityUnreviewedSummary,
  QualityRecalculateRequest,
  QualityRecalculateResponse,
  ResearchJobActionResponse,
  ResearchDataAssetsResponse,
  ResearchDataGapsResponse,
  ResearchDataImportRunsResponse,
  ResearchDataProvidersResponse,
  ResearchDataQualityResponse,
  ResearchJobDetailResponse,
  ResearchJobListResponse,
} from "../types";

export async function getResearchDataAssets(): Promise<ResearchDataAssetsResponse> {
  return apiRequest<ResearchDataAssetsResponse>("/research/data/assets", { method: "GET" });
}

export async function getResearchDataProviders(): Promise<ResearchDataProvidersResponse> {
  return apiRequest<ResearchDataProvidersResponse>("/research/data/providers", { method: "GET" });
}

export async function getResearchDataCoverage(): Promise<ResearchDataAssetsResponse> {
  return apiRequest<ResearchDataAssetsResponse>("/research/data/coverage", { method: "GET" });
}

export async function getResearchDataQuality(): Promise<ResearchDataQualityResponse> {
  return apiRequest<ResearchDataQualityResponse>("/research/data/quality", { method: "GET" });
}

export async function getResearchDataGaps(): Promise<ResearchDataGapsResponse> {
  return apiRequest<ResearchDataGapsResponse>("/research/data/gaps", { method: "GET" });
}

export async function getResearchDataImportRuns(): Promise<ResearchDataImportRunsResponse> {
  return apiRequest<ResearchDataImportRunsResponse>("/research/data/import-runs", { method: "GET" });
}

export async function recalculateResearchDataQuality(
  payload: QualityRecalculateRequest,
): Promise<QualityRecalculateResponse> {
  return apiRequest<QualityRecalculateResponse>("/research/data/quality/recalculate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function startResearchImportJob(payload: {
  assets: string[];
  timeframes: string[];
  requested_years: number;
  providers: string[];
  dry_run: boolean;
}): Promise<ResearchJobDetailResponse> {
  return apiRequest<ResearchJobDetailResponse>("/research/jobs/import", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function startResearchQualityJob(
  payload: QualityRecalculateRequest,
): Promise<ResearchJobDetailResponse> {
  return apiRequest<ResearchJobDetailResponse>("/research/jobs/quality/recalculate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getResearchJobs(): Promise<ResearchJobListResponse> {
  return apiRequest<ResearchJobListResponse>("/research/jobs", { method: "GET" });
}

export async function getResearchJob(jobId: string): Promise<ResearchJobDetailResponse> {
  return apiRequest<ResearchJobDetailResponse>(`/research/jobs/${jobId}`, { method: "GET" });
}

export async function cancelResearchJob(jobId: string): Promise<ResearchJobActionResponse> {
  return apiRequest<ResearchJobActionResponse>(`/research/jobs/${jobId}/cancel`, { method: "POST" });
}

export async function retryResearchJob(jobId: string): Promise<ResearchJobActionResponse> {
  return apiRequest<ResearchJobActionResponse>(`/research/jobs/${jobId}/retry`, { method: "POST" });
}

// ── MH-12/13 Data Quality Review ────────────────────────────────────────

export async function getDataQualityOutliers(params?: {
  reviewStatus?: string;
  asset?: string;
  provider?: string;
  timeframe?: string;
  limit?: number;
  offset?: number;
}): Promise<DataQualityOutliersResponse> {
  const qs = new URLSearchParams();
  if (params?.reviewStatus) qs.set("review_status", params.reviewStatus);
  if (params?.asset) qs.set("asset", params.asset);
  if (params?.provider) qs.set("provider", params.provider);
  if (params?.timeframe) qs.set("timeframe", params.timeframe);
  if (params?.limit != null) qs.set("limit", String(params.limit));
  if (params?.offset != null) qs.set("offset", String(params.offset));
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return apiRequest<DataQualityOutliersResponse>(`/research/data/quality/outliers${suffix}`, {
    method: "GET",
  });
}

export async function reviewDataQualityOutlier(
  reportId: string,
  request: DataQualityReviewRequest,
): Promise<DataQualityReviewResponse> {
  return apiRequest<DataQualityReviewResponse>(
    `/research/data/quality/outliers/${reportId}/review`,
    {
      method: "POST",
      body: JSON.stringify(request),
    },
  );
}

export async function getDataQualityAuditTrail(
  reportId: string,
): Promise<DataQualityAuditResponse> {
  return apiRequest<DataQualityAuditResponse>(
    `/research/data/quality/outliers/${reportId}/audit`,
    { method: "GET" },
  );
}

export async function getDataQualitySummary(): Promise<DataQualityUnreviewedSummary> {
  return apiRequest<DataQualityUnreviewedSummary>("/research/data/quality/outliers/summary", {
    method: "GET",
  });
}
