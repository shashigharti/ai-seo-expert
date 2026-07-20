import { AgentExecutionCard } from "./AgentExecutionCard";
import { PULL_REQUEST_CAPABILITY_PREFIX } from "../../features/agentExecution/types";
import { useAgentExecution } from "../../features/agentExecution/useAgentExecution";

const isSeoCapability = (capability: string) => !capability.startsWith(PULL_REQUEST_CAPABILITY_PREFIX);

/** docs/specs.md's right-hand "Agent Execution Panel" - a live multi-agent
 * execution timeline (docs/specs.md §4/Layout) for the SEO analysis
 * pipeline specifically. Named "SEO Agent Execution" to distinguish it from
 * GitHubPRExecutionPanel, its sibling for the PR-generation pipeline -
 * both share useAgentExecution, filtered to opposite capability subsets.
 * Renders once a workflow exists; useAgentExecution handles the initial
 * REST snapshot + live SSE deltas (see that hook for why both are needed). */
export function AgentExecutionPanel({ workflowId }: { workflowId: string }) {
  const { tasks, isConnected, error } = useAgentExecution(workflowId, isSeoCapability);

  const totalTokens = tasks.reduce((sum, task) => sum + (task.token_usage?.total_tokens ?? 0), 0);
  const totalCost = tasks.reduce((sum, task) => sum + (task.estimated_cost_usd ?? 0), 0);
  const completedCount = tasks.filter((task) => task.status === "completed" || task.status === "failed").length;

  return (
    <div className="card p-4 shadow-sm">
      <div className="d-flex justify-content-between align-items-start mb-3">
        <h2 className="h5 mb-0 d-flex align-items-center gap-2">
          <i className="bi bi-robot text-primary" aria-hidden="true" />
          SEO Agent Execution
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
          <i className="bi bi-hourglass-split" aria-hidden="true" />
          Waiting for agents to start…
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
              {completedCount}/{tasks.length} agents finished
            </span>
            <span>
              <i className="bi bi-coin me-1" aria-hidden="true" />
              {totalTokens} tokens
            </span>
            <span>
              <i className="bi bi-currency-dollar me-1" aria-hidden="true" />
              {totalCost.toFixed(5)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
