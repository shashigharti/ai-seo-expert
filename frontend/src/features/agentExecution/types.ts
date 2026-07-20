export type TaskExecutionStatus = "pending" | "running" | "completed" | "failed";

/** Every PR-generation task's `capability` carries this prefix (backend:
 * app/application/pull_requests/service.py's CAPABILITY_PREFIX) - the only
 * thing distinguishing it from a SEO analysis capability task on the wire.
 * Used to split one shared task/event stream between AgentExecutionPanel
 * (SEO) and GitHubPRExecutionPanel (PR generation). */
export const PULL_REQUEST_CAPABILITY_PREFIX = "pull_request_";

export interface TokenUsage {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  /** Subset of output_tokens spent on thinking-mode reasoning (not
   * additive), null when the agent didn't use thinking mode. */
  reasoning_tokens: number | null;
}

/** Mirrors the backend's WorkflowEvent (app/domain/models/event.py) -
 * pushed live over GET /api/workflows/{id}/events. */
export interface WorkflowEvent {
  type: string;
  workflow_id: string;
  task_id: string | null;
  capability: string | null;
  status: TaskExecutionStatus | null;
  data: {
    agent_name?: string;
    confidence?: number;
    token_usage?: { input_tokens: number; output_tokens: number; reasoning_tokens?: number | null };
    model?: string;
    duration_seconds?: number;
    findings_count?: number;
    limitations?: string[];
    error_message?: string;
    reasoning?: string | null;
  } | null;
}

/** Mirrors the backend's TaskResponse (app/api/schemas/task.py) - the
 * initial snapshot from GET /api/workflows/{id}/tasks, kept up to date
 * afterward by folding in live WorkflowEvents (see useAgentExecution). */
export interface TaskExecution {
  id: string;
  workflow_id: string;
  capability: string;
  status: TaskExecutionStatus;
  attempt: number;
  max_attempts: number;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  agent_name: string | null;
  confidence: number | null;
  token_usage: TokenUsage | null;
  model: string | null;
  estimated_cost_usd: number | null;
  findings_count: number | null;
  limitations: string[];
  error_message: string | null;
  reasoning: string | null;
}

export interface TaskExecutionListResponse {
  items: TaskExecution[];
}
