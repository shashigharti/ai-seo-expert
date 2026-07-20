import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../../services/apiClient";
import { createWorkflow, getWorkflow } from "./api";
import type { CreateWorkflowInput, Workflow } from "./types";

interface UseWorkflowState {
  workflow: Workflow | null;
  isLoading: boolean;
  error: string | null;
}

const TERMINAL_STATUSES = new Set<Workflow["status"]>(["completed", "failed"]);
const POLL_INTERVAL_MS = 3000;

export function useWorkflow() {
  const [state, setState] = useState<UseWorkflowState>({
    workflow: null,
    isLoading: false,
    error: null,
  });

  // Returns whether the submission actually succeeded - WorkflowForm only
  // clears the URL the user typed once it knows that, instead of
  // optimistically clearing it before the request even resolves (which
  // silently threw away what they typed on any failure, e.g. the backend
  // being unreachable).
  const submit = useCallback(async (input: CreateWorkflowInput): Promise<boolean> => {
    setState({ workflow: null, isLoading: true, error: null });
    try {
      const workflow = await createWorkflow(input);
      setState({ workflow, isLoading: false, error: null });
      return true;
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Failed to create workflow";
      setState({ workflow: null, isLoading: false, error: message });
      return false;
    }
  }, []);

  const load = useCallback(async (workflowId: string) => {
    setState({ workflow: null, isLoading: true, error: null });
    try {
      const workflow = await getWorkflow(workflowId);
      setState({ workflow, isLoading: false, error: null });
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Failed to load workflow";
      setState({ workflow: null, isLoading: false, error: message });
    }
  }, []);

  // The background analysis run (backend/app/application/workflows/
  // analysis_runner.py) has no push channel of its own - poll for status
  // until it reaches a terminal one, so a background-task failure (bad
  // Qwen/GitHub credentials, a network error, etc.) actually reaches
  // WorkflowStatusCard instead of leaving the status stuck at whatever it
  // was when the page loaded.
  const workflowId = state.workflow?.id;
  const workflowStatus = state.workflow?.status;
  useEffect(() => {
    if (!workflowId || !workflowStatus || TERMINAL_STATUSES.has(workflowStatus)) return;

    let cancelled = false;
    const interval = setInterval(async () => {
      try {
        const workflow = await getWorkflow(workflowId);
        if (!cancelled) setState((prev) => ({ ...prev, workflow }));
      } catch {
        // A transient poll failure isn't worth surfacing - the next tick retries.
      }
    }, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [workflowId, workflowStatus]);

  return { ...state, submit, load };
}
