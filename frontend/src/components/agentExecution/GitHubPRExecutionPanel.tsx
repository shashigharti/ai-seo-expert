import { AgentExecutionCard } from "./AgentExecutionCard";
import { PULL_REQUEST_CAPABILITY_PREFIX } from "../../features/agentExecution/types";
import { useAgentExecution } from "../../features/agentExecution/useAgentExecution";

const isPullRequestCapability = (capability: string) => capability.startsWith(PULL_REQUEST_CAPABILITY_PREFIX);

/** Sibling to AgentExecutionPanel ("SEO Agent Execution") for the PR
 * generation pipeline (docs/specs.md §3's "Trigger PR generation... Display
 * generation progress" and the Non-Functional "real-time updates via SSE"
 * requirement, neither scoped only to SEO analysis). Each FixGroup is
 * dispatched as its own Task through the same Orchestrator SEO capability
 * workers use (backend/app/application/pull_requests/service.py), so this
 * shares useAgentExecution/AgentExecutionCard rather than duplicating them
 * - only the capability filter differs. */
export function GitHubPRExecutionPanel({ workflowId }: { workflowId: string }) {
  const { tasks, isConnected, error } = useAgentExecution(workflowId, isPullRequestCapability);

  const totalTokens = tasks.reduce((sum, task) => sum + (task.token_usage?.total_tokens ?? 0), 0);
  const completedCount = tasks.filter((task) => task.status === "completed" || task.status === "failed").length;

  return (
    <div className="card p-4 shadow-sm">
      <div className="d-flex justify-content-between align-items-start mb-3">
        <h2 className="h5 mb-0 d-flex align-items-center gap-2">
          <i className="bi bi-git text-primary" aria-hidden="true" />
          GitHub PR Agent Execution
        </h2>
        <span
          className={`badge d-flex align-items-center gap-2 ${isConnected ? "text-bg-success" : "text-bg-secondary"}`}
          aria-live="polite"
        >
          {isConnected ? (
            <span className="live-dot" aria-hidden="true" />
          ) : (
            <i className="bi bi-hourglass-split" aria-hidden="true" />
          )}
          {isConnected ? "Live" : "Connecting…"}
        </span>
      </div>

      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}

      {tasks.length === 0 && !error && (
        <p className="text-secondary small mb-0 d-flex align-items-center gap-2">
          <i className="bi bi-info-circle" aria-hidden="true" />
          No pull requests generated yet - approve findings and generate a pull request to see progress here.
        </p>
      )}

      {tasks.map((task) => (
        <AgentExecutionCard key={task.id} task={task} />
      ))}

      {tasks.length > 0 && (
        <div className="border-top pt-2 mt-2 small text-secondary">
          <div className="d-flex justify-content-between">
            <span>
              <i className="bi bi-list-task me-1" aria-hidden="true" />
              {completedCount}/{tasks.length} pull request(s) finished
            </span>
            <span>
              <i className="bi bi-coin me-1" aria-hidden="true" />
              {totalTokens} tokens
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
