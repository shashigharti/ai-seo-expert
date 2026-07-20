import { useEffect, useRef, useState } from "react";
import { subscribeToWorkflowEvents } from "../../services/sseClient";
import { getTasks } from "./api";
import type { TaskExecution, WorkflowEvent } from "./types";

function applyEvent(
  tasksById: Map<string, TaskExecution>,
  event: WorkflowEvent,
  capabilityFilter: (capability: string) => boolean
): Map<string, TaskExecution> {
  if (!event.task_id) return tasksById;

  const now = new Date().toISOString();
  const existing = tasksById.get(event.task_id);
  const next = new Map(tasksById);

  if (event.type === "task.created") {
    if (!capabilityFilter(event.capability ?? existing?.capability ?? "unknown")) return tasksById;
    next.set(event.task_id, {
      id: event.task_id,
      workflow_id: event.workflow_id,
      capability: event.capability ?? existing?.capability ?? "unknown",
      status: "pending",
      attempt: existing?.attempt ?? 0,
      max_attempts: existing?.max_attempts ?? 3,
      created_at: existing?.created_at ?? now,
      updated_at: now,
      started_at: null,
      agent_name: null,
      confidence: null,
      token_usage: null,
      model: null,
      estimated_cost_usd: null,
      findings_count: null,
      limitations: [],
      error_message: null,
      reasoning: null,
    });
    return next;
  }

  if (!existing) return tasksById; // an update for a task we haven't seen a "created" event for yet

  if (event.type === "task.started") {
    next.set(event.task_id, { ...existing, status: "running", started_at: existing.started_at ?? now, updated_at: now });
    return next;
  }

  if (event.type === "task.retrying") {
    next.set(event.task_id, { ...existing, status: "pending", updated_at: now });
    return next;
  }

  if (event.type === "task.completed" || event.type === "task.failed") {
    const data = event.data;
    const tokenUsage = data?.token_usage
      ? {
          input_tokens: data.token_usage.input_tokens,
          output_tokens: data.token_usage.output_tokens,
          total_tokens: data.token_usage.input_tokens + data.token_usage.output_tokens,
          reasoning_tokens: data.token_usage.reasoning_tokens ?? null,
        }
      : existing.token_usage;
    next.set(event.task_id, {
      ...existing,
      status: event.type === "task.completed" ? "completed" : "failed",
      updated_at: now,
      agent_name: data?.agent_name ?? existing.agent_name,
      confidence: data?.confidence ?? existing.confidence,
      token_usage: tokenUsage,
      model: data?.model ?? existing.model,
      findings_count: data?.findings_count ?? existing.findings_count,
      limitations: data?.limitations ?? existing.limitations,
      error_message: data?.error_message ?? existing.error_message,
      reasoning: data?.reasoning ?? existing.reasoning,
    });
    return next;
  }

  return tasksById;
}

const ACCEPT_ALL_CAPABILITIES = () => true;

/** Backs both the SEO Agent Execution Panel and the GitHub PR Agent
 * Execution Panel - both watch the same per-workflow task/event streams
 * (GET /tasks + GET /events), differing only in which capabilities they
 * care about. `capabilityFilter` lets each panel pick its own subset
 * (SEO: everything except `pull_request_*`; PR: only `pull_request_*`)
 * while sharing this hook instead of duplicating it; each still opens its
 * own EventSource (no shared subscription/context - see
 * AgentExecutionPanel.tsx / GitHubPRExecutionPanel.tsx).
 */
export function useAgentExecution(
  workflowId: string | null,
  capabilityFilter: (capability: string) => boolean = ACCEPT_ALL_CAPABILITIES
) {
  const [tasks, setTasks] = useState<TaskExecution[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const tasksByIdRef = useRef(new Map<string, TaskExecution>());

  useEffect(() => {
    if (!workflowId) return;

    tasksByIdRef.current = new Map();
    setTasks([]);
    setError(null);

    let cancelled = false;

    getTasks(workflowId)
      .then((response) => {
        if (cancelled) return;
        const byId = new Map(
          response.items.filter((task) => capabilityFilter(task.capability)).map((task) => [task.id, task] as const)
        );
        tasksByIdRef.current = byId;
        setTasks(Array.from(byId.values()));
      })
      .catch(() => {
        if (!cancelled) setError("Failed to load agent execution state");
      });

    const unsubscribe = subscribeToWorkflowEvents(
      workflowId,
      (event) => {
        tasksByIdRef.current = applyEvent(tasksByIdRef.current, event, capabilityFilter);
        setTasks(
          Array.from(tasksByIdRef.current.values()).sort((a, b) => a.created_at.localeCompare(b.created_at))
        );
        setIsConnected(true);
      },
      () => setIsConnected(false),
      () => setIsConnected(true)
    );

    return () => {
      cancelled = true;
      unsubscribe();
    };
    // capabilityFilter is expected to be a stable reference per caller (a
    // module-level function, e.g. isSeoCapability/isPullRequestCapability) -
    // included here for correctness, not expected to actually change often.
  }, [workflowId, capabilityFilter]);

  return { tasks, isConnected, error };
}
