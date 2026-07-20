import { useCallback, useEffect, useState } from "react";
import { PULL_REQUEST_CAPABILITY_PREFIX } from "../agentExecution/types";
import { subscribeToWorkflowEvents } from "../../services/sseClient";
import { ApiError } from "../../services/apiClient";
import { generatePullRequests, getPullRequests } from "./api";
import type { PullRequestResult } from "./types";

interface UsePullRequestsState {
  results: PullRequestResult[];
  isGenerating: boolean;
  error: string | null;
}

/** PR generation now runs in the background (POST returns immediately -
 * see docs/api-contracts.md), so `results` no longer comes from the
 * generate() response body. It's populated by `refresh()` (GET
 * /pull-requests), called on mount (findings/PRs can already exist from a
 * previous page load) and automatically whenever a `pull_request_*` task
 * settles - GitHubPRExecutionPanel shows live per-group progress off the
 * same event stream; this hook only needs to know *when* to refetch. */
export function usePullRequests(workflowId: string) {
  const [state, setState] = useState<UsePullRequestsState>({ results: [], isGenerating: false, error: null });

  const refresh = useCallback(async () => {
    try {
      const data = await getPullRequests(workflowId);
      setState((prev) => ({ ...prev, results: data.items }));
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Failed to load pull requests";
      setState((prev) => ({ ...prev, error: message }));
    }
  }, [workflowId]);

  useEffect(() => {
    void refresh();

    const unsubscribe = subscribeToWorkflowEvents(workflowId, (event) => {
      const isSettledPullRequestTask =
        (event.type === "task.completed" || event.type === "task.failed") &&
        (event.capability ?? "").startsWith(PULL_REQUEST_CAPABILITY_PREFIX);
      if (isSettledPullRequestTask) void refresh();
    });

    return unsubscribe;
  }, [workflowId, refresh]);

  const generate = useCallback(
    async (prStrategy: string) => {
      setState((prev) => ({ ...prev, isGenerating: true, error: null }));
      try {
        await generatePullRequests(workflowId, prStrategy);
        setState((prev) => ({ ...prev, isGenerating: false }));
      } catch (error) {
        const message = error instanceof ApiError ? error.message : "Failed to generate pull request";
        setState((prev) => ({ ...prev, isGenerating: false, error: message }));
      }
    },
    [workflowId],
  );

  return { ...state, refresh, generate };
}
