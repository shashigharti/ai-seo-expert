export type PullRequestStatus = "opened" | "failed";

export interface PullRequestResult {
  id: string;
  workflow_id: string;
  status: PullRequestStatus;
  url: string | null;
  repository_url: string;
  branch_name: string;
  commit_summary: string;
  finding_ids: string[];
  error_message: string | null;
  created_at: string;
}

export interface PullRequestListResponse {
  items: PullRequestResult[];
}

/** POST /pull-requests's response - generation now runs in the background
 * (see docs/api-contracts.md), so this returns immediately with the task
 * ids to watch (GitHubPRExecutionPanel) rather than final results. Final
 * results are fetched separately via getPullRequests once tasks settle. */
export interface PullRequestGenerationStartedResponse {
  task_ids: string[];
}
