export type WorkflowStatus = "pending" | "running" | "awaiting_approval" | "completed" | "failed";

export interface Workflow {
  id: string;
  repository_url: string;
  branch: string;
  goal: string;
  status: WorkflowStatus;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

// No `goal` field - the manager plans against a fixed internal default
// (backend/app/domain/models/workflow.py: DEFAULT_GOAL). Never asked of
// the user; this app's job is simply "find SEO issues in this repo."
export interface CreateWorkflowInput {
  repository_url: string;
  branch?: string;
}
