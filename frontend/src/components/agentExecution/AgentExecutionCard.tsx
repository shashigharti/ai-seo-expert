import { useState } from "react";
import { humanizeAgentLabel } from "../common/textFormat";
import {
  TASK_EXECUTION_STATUS_BORDER_CLASS,
  TASK_EXECUTION_STATUS_ICON,
  TASK_EXECUTION_STATUS_LABEL,
} from "../common/statusMaps";
import type { TaskExecution } from "../../features/agentExecution/types";

function formatDuration(task: TaskExecution): string | null {
  if (!task.started_at) return null;
  const end = task.status === "completed" || task.status === "failed" ? task.updated_at : new Date().toISOString();
  const seconds = (new Date(end).getTime() - new Date(task.started_at).getTime()) / 1000;
  return seconds < 1 ? `${Math.round(seconds * 1000)}ms` : `${seconds.toFixed(1)}s`;
}

/** The model's reasoning trace is one continuous stream (DashScope's
 * `reasoning_content`, joined across ThinkingPart segments - see backend's
 * _extract_reasoning), but it naturally breaks into paragraphs as the
 * model moves from one consideration to the next. Splitting on those blank
 * lines is what turns it into discrete timeline steps below, rather than
 * one dense wall of text - the real reasoning, just structured for
 * scanning instead of reading start to end. */
function splitReasoningIntoSteps(reasoning: string): string[] {
  return reasoning
    .split(/\n\s*\n+/)
    .map((step) => step.trim())
    .filter(Boolean);
}

/** A status icon (spinner while running, a static bi-* icon otherwise) -
 * paired with the text label below rather than color alone, so status is
 * never conveyed by color alone (docs/system-design.md §9 accessibility). */
function StatusIndicator({ status }: { status: TaskExecution["status"] }) {
  if (status === "running") {
    return <span className="spinner-border spinner-border-sm text-primary" aria-hidden="true" />;
  }
  const colorClass = TASK_EXECUTION_STATUS_BORDER_CLASS[status].replace("border-", "text-");
  return <i className={`bi ${TASK_EXECUTION_STATUS_ICON[status]} ${colorClass}`} aria-hidden="true" />;
}

/** docs/specs.md §4 Agent Execution Panel: agent name, status, duration,
 * tokens, model, and a short decision summary per agent execution, plus
 * (when the agent's model policy has thinking enabled - see
 * docs/agent-architecture.md §6) its real thinking-mode reasoning trace as
 * an expandable "intermediate steps" disclosure - collapsed by default
 * (docs/specs.md's "expandable sections for advanced details without
 * overwhelming users"), since traces can run long. Absent entirely for
 * agents that don't use thinking mode; there's no trace to show, not a
 * placeholder for one.
 *
 * A plain `.list-row` rather than its own `.card` - this already sits
 * inside AgentExecutionPanel's card, and a card-in-a-card per task read as
 * a stack of boxes inside a box. Status is carried by StatusIndicator's
 * icon + the text label next to it (never color alone), so the previous
 * border-start color accent was decorative on top of that, not additional
 * information. */
export function AgentExecutionCard({ task }: { task: TaskExecution }) {
  const duration = formatDuration(task);
  const [showReasoning, setShowReasoning] = useState(false);

  return (
    <div className="list-row">
      <div className="d-flex justify-content-between align-items-center">
        <span className="fw-semibold d-flex align-items-center gap-2">
          <i className="bi bi-cpu text-secondary" aria-hidden="true" />
          {humanizeAgentLabel(task.agent_name ?? task.capability)}
        </span>
        <span className="d-flex align-items-center gap-1 small text-secondary">
          <StatusIndicator status={task.status} />
          {TASK_EXECUTION_STATUS_LABEL[task.status]}
        </span>
      </div>
      <div className="d-flex flex-wrap gap-3 text-secondary small mt-1">
        {duration && (
          <span>
            <i className="bi bi-clock-history me-1" aria-hidden="true" />
            {duration}
          </span>
        )}
        {task.token_usage && (
          <span>
            <i className="bi bi-coin me-1" aria-hidden="true" />
            {task.token_usage.total_tokens} tokens
            {task.token_usage.reasoning_tokens != null && ` (${task.token_usage.reasoning_tokens} reasoning)`}
          </span>
        )}
        {task.model && (
          <span>
            <i className="bi bi-cpu-fill me-1" aria-hidden="true" />
            {task.model}
          </span>
        )}
        {task.estimated_cost_usd != null && (
          <span>
            <i className="bi bi-currency-dollar me-1" aria-hidden="true" />
            {task.estimated_cost_usd.toFixed(5)}
          </span>
        )}
      </div>
      {task.status === "completed" && (
        <p className="small mb-0 mt-1">
          {task.findings_count != null
            ? `Found ${task.findings_count} finding${task.findings_count === 1 ? "" : "s"}`
            : "Completed"}
          {task.limitations.length > 0 && ` - ${task.limitations.join("; ")}`}
        </p>
      )}
      {task.status === "failed" && (
        <p className="small mb-0 mt-1 text-danger">
          Failed after {task.attempt} attempt(s){task.error_message && ` - ${task.error_message}`}
        </p>
      )}
      {task.reasoning && (
        <div className="mt-1">
          <button
            type="button"
            className="btn btn-link btn-sm p-0 small text-decoration-none d-inline-flex align-items-center gap-1"
            onClick={() => setShowReasoning((prev) => !prev)}
            aria-expanded={showReasoning}
          >
            <i className={`bi ${showReasoning ? "bi-chevron-down" : "bi-chevron-right"}`} aria-hidden="true" />
            {showReasoning ? "Hide reasoning" : "Show reasoning"}
          </button>
          {showReasoning && (
            <ol className="reasoning-timeline small text-secondary mt-2 mb-0">
              {splitReasoningIntoSteps(task.reasoning).map((step, index) => (
                <li key={index} className="reasoning-timeline-step">
                  {step}
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </div>
  );
}
