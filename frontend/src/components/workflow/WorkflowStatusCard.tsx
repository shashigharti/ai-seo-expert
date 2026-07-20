import { StatusBadge } from "../common/StatusBadge";
import { WORKFLOW_STATUS_BADGE_CLASS } from "../common/statusMaps";
import type { Workflow } from "../../features/workflows/types";

interface WorkflowStatusCardProps {
  workflow: Workflow;
}

export function WorkflowStatusCard({ workflow }: WorkflowStatusCardProps) {
  return (
    <div className="card p-4 shadow-sm">
      <div className="d-flex justify-content-between align-items-start">
        <h2 className="h5 mb-3 d-flex align-items-center gap-2">
          <i className="bi bi-diagram-3 text-primary" aria-hidden="true" />
          Workflow
        </h2>
        <div className="d-flex align-items-center gap-2">
          {workflow.status === "running" && (
            <span className="spinner-border spinner-border-sm text-primary" aria-hidden="true" />
          )}
          <StatusBadge status={workflow.status} classMap={WORKFLOW_STATUS_BADGE_CLASS} />
        </div>
      </div>
      <div className="meta-grid">
        <div className="meta-item">
          <span className="meta-label">ID</span>
          <code className="meta-value">{workflow.id}</code>
        </div>
        <div className="meta-item">
          <span className="meta-label">Repository</span>
          <span className="meta-value">{workflow.repository_url}</span>
        </div>
        <div className="meta-item">
          <span className="meta-label">Branch</span>
          <code className="meta-value">{workflow.branch}</code>
        </div>
        <div className="meta-item">
          <span className="meta-label">Created</span>
          <span className="meta-value">{new Date(workflow.created_at).toLocaleString()}</span>
        </div>
      </div>
      {workflow.status === "failed" && workflow.error_message && (
        <div className="alert alert-danger d-flex align-items-center gap-2 mb-0 mt-3" role="alert">
          <i className="bi bi-exclamation-triangle flex-shrink-0" aria-hidden="true" />
          {workflow.error_message}
        </div>
      )}
    </div>
  );
}
