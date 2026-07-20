import { getRequest, postRequest } from "../../services/apiClient";
import type { PullRequestGenerationStartedResponse, PullRequestListResponse } from "./types";

export function generatePullRequests(
  workflowId: string,
  prStrategy: string,
): Promise<PullRequestGenerationStartedResponse> {
  return postRequest<PullRequestGenerationStartedResponse>(`/api/workflows/${workflowId}/pull-requests`, {
    pr_strategy: prStrategy,
  });
}

export function getPullRequests(workflowId: string): Promise<PullRequestListResponse> {
  return getRequest<PullRequestListResponse>(`/api/workflows/${workflowId}/pull-requests`);
}
