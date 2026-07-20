import type { TaskExecutionStatus } from "../../features/agentExecution/types";
import type { FindingStatus, Severity } from "../../features/findings/types";
import type { PullRequestStatus } from "../../features/pullRequests/types";
import type { WorkflowStatus } from "../../features/workflows/types";

// docs/system-design.md §5 Status Mapping / §6 Severity Mapping - the single
// source for every status-to-Bootstrap-color mapping in the app. Previously
// duplicated by hand across severityBadge.ts, WorkflowStatusCard.tsx, and
// PullRequestResultCard.tsx.
export const SEVERITY_BADGE_CLASS: Record<Severity, string> = {
  critical: "text-bg-danger",
  high: "text-bg-warning",
  medium: "text-bg-info",
  low: "text-bg-secondary",
};

export const FINDING_STATUS_BADGE_CLASS: Record<FindingStatus, string> = {
  pending: "text-bg-secondary",
  approved: "text-bg-success",
  rejected: "text-bg-dark",
};

export const WORKFLOW_STATUS_BADGE_CLASS: Record<WorkflowStatus, string> = {
  pending: "text-bg-secondary",
  running: "text-bg-primary",
  awaiting_approval: "text-bg-warning",
  completed: "text-bg-success",
  failed: "text-bg-danger",
};

export const PULL_REQUEST_STATUS_BADGE_CLASS: Record<PullRequestStatus, string> = {
  opened: "text-bg-success",
  failed: "text-bg-danger",
};

export const TASK_EXECUTION_STATUS_BORDER_CLASS: Record<TaskExecutionStatus, string> = {
  pending: "border-secondary",
  running: "border-primary",
  completed: "border-success",
  failed: "border-danger",
};

// bi-* icon per status (except "running", which shows a spinner instead -
// a static icon can't convey "in progress" as clearly as motion can).
export const TASK_EXECUTION_STATUS_ICON: Record<Exclude<TaskExecutionStatus, "running">, string> = {
  pending: "bi-hourglass-split",
  completed: "bi-check-circle-fill",
  failed: "bi-x-circle-fill",
};

// docs/specs.md §4 calls the "pending" state "Waiting" in the Agent
// Execution Panel specifically - the wire status stays "pending" (matching
// TaskStatus everywhere else), this is presentation-only.
export const TASK_EXECUTION_STATUS_LABEL: Record<TaskExecutionStatus, string> = {
  pending: "Waiting",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
};
