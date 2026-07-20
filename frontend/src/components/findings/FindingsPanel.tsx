import { useEffect, useState } from "react";
import { ApprovalBar } from "../approval/ApprovalBar";
import { humanizeAgentLabel } from "../common/textFormat";
import { FindingCard } from "./FindingCard";
import { FindingsSummary } from "./FindingsSummary";
import { useFindings } from "../../features/findings/useFindings";
import type { Severity, StoredFinding } from "../../features/findings/types";
import type { WorkflowStatus } from "../../features/workflows/types";

const TERMINAL_WORKFLOW_STATUSES = new Set<WorkflowStatus>(["completed", "failed"]);

interface FindingsPanelProps {
  workflowId: string;
  /** The workflow's current status - once it reaches a terminal state,
   * findings are refetched automatically (see the effect below) rather
   * than requiring the user to click Refresh. Findings are only ever
   * persisted once, right at the end of the SEO analysis run (backend:
   * run_seo_analysis's _review_and_persist), so "the SEO Agent Execution
   * finished" and "the workflow's own status went terminal" are the same
   * event - there's no separate push for "findings are ready". */
  workflowStatus: WorkflowStatus;
  /** Called with the actual pr_strategy used, once approval succeeds - lets
   * PullRequestPanel generate against the strategy that was really chosen
   * here, instead of a hardcoded default. */
  onApproved?: (prStrategy: string) => void;
  /** Reports whether *any* real, already-fetched finding has left "pending"
   * - re-derived every time `data` changes (initial load, refresh, or
   * right after a fresh approve(), which itself refreshes `data`). This is
   * what WorkflowSteps' "Approve" step should watch, not a one-shot flag
   * set only inside a fresh approve() call: that flag stays false forever
   * if approval happened in an earlier session/page load (e.g. you
   * reloaded the results page, or came back after generating a PR), even
   * though the real backend data already shows an approved finding. */
  onApprovalStateChange?: (hasApprovedAny: boolean) => void;
}

const SEVERITY_ORDER: Record<Severity, number> = { critical: 0, high: 1, medium: 2, low: 3 };

/** Grouped by the SEO agent task that produced each finding
 * (StoredFinding.agent_name - every finding's originating capability
 * worker, e.g. "MetadataAgent"/"AccessibilityAgent"), sorted by severity
 * within each group - mirrors how the SEO Agent Execution Panel already
 * organizes work by agent, rather than by the finding's own category. */
function groupByAgent(items: StoredFinding[]): [string, StoredFinding[]][] {
  const byAgent = new Map<string, StoredFinding[]>();
  for (const item of items) {
    const list = byAgent.get(item.agent_name) ?? [];
    list.push(item);
    byAgent.set(item.agent_name, list);
  }
  for (const list of byAgent.values()) {
    list.sort((a, b) => SEVERITY_ORDER[a.finding.severity] - SEVERITY_ORDER[b.finding.severity]);
  }
  return Array.from(byAgent.entries()).sort(([a], [b]) => a.localeCompare(b));
}

export function FindingsPanel({
  workflowId,
  workflowStatus,
  onApproved,
  onApprovalStateChange,
}: FindingsPanelProps) {
  const { data, isLoading, error, isApproving, refresh, approve } = useFindings(workflowId);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    onApprovalStateChange?.(data?.items.some((item) => item.status !== "pending") ?? false);
  }, [data, onApprovalStateChange]);

  // Re-fetch whenever the workflow transitions into a terminal state - this
  // only re-runs on an actual status change (not every render), so a
  // workflow that's already terminal when the panel mounts is covered by
  // the effect above instead, and this one fires exactly once, right when
  // the SEO Agent Execution Panel would show every agent as finished.
  useEffect(() => {
    if (TERMINAL_WORKFLOW_STATUSES.has(workflowStatus)) void refresh();
  }, [workflowStatus, refresh]);

  const toggleSelected = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleApprove = async (prStrategy: string) => {
    const response = await approve(Array.from(selectedIds), prStrategy);
    setSelectedIds(new Set());
    onApproved?.(response.pr_strategy);
  };

  return (
    <div className="card p-4 shadow-sm">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h2 className="h5 mb-0 d-flex align-items-center gap-2">
          <i className="bi bi-list-check text-primary" aria-hidden="true" />
          Findings
        </h2>
        <button
          type="button"
          className="btn btn-outline-secondary btn-sm rounded-pill d-inline-flex align-items-center gap-2"
          onClick={() => void refresh()}
        >
          {isLoading ? (
            <span className="spinner-border spinner-border-sm" aria-hidden="true" />
          ) : (
            <i className="bi bi-arrow-clockwise" aria-hidden="true" />
          )}
          {isLoading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}

      {data && data.total === 0 && !isLoading && (
        <p className="text-secondary mb-0 d-flex align-items-center gap-2">
          <i className="bi bi-hourglass-split" aria-hidden="true" />
          No findings yet. Analysis may still be in progress - check back shortly or refresh.
        </p>
      )}

      {data && data.total > 0 && (
        <>
          <FindingsSummary summary={data} />
          {groupByAgent(data.items).map(([agentName, items]) => (
            <div key={agentName} className="finding-group mb-3">
              <h3 className="finding-group-heading mb-2 d-flex align-items-center gap-2">
                <i className="bi bi-cpu text-secondary" aria-hidden="true" />
                {humanizeAgentLabel(agentName)}
                <span className="badge text-bg-light border rounded-pill">{items.length}</span>
              </h3>
              <div className="accordion">
                {items.map((item) => (
                  <FindingCard
                    key={item.id}
                    storedFinding={item}
                    selected={selectedIds.has(item.id)}
                    onToggle={toggleSelected}
                  />
                ))}
              </div>
            </div>
          ))}
          <div className="mt-3">
            <ApprovalBar
              selectedCount={selectedIds.size}
              isApproving={isApproving}
              onApprove={handleApprove}
            />
          </div>
        </>
      )}
    </div>
  );
}
