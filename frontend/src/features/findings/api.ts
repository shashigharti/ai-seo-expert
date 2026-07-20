import { getRequest, postRequest } from "../../services/apiClient";
import type { ApprovalResponse, FindingListResponse } from "./types";

export function getFindings(workflowId: string): Promise<FindingListResponse> {
  return getRequest<FindingListResponse>(`/api/workflows/${workflowId}/findings`);
}

export function approveFindings(
  workflowId: string,
  findingIds: string[],
  prStrategy: string,
): Promise<ApprovalResponse> {
  return postRequest<ApprovalResponse>(`/api/workflows/${workflowId}/approvals`, {
    finding_ids: findingIds,
    pr_strategy: prStrategy,
  });
}
