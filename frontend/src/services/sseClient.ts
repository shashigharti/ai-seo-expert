import type { WorkflowEvent } from "../features/agentExecution/types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

/**
 * A sibling to apiClient.ts, not an extension of it - getRequest/postRequest
 * both await response.json() the whole body, which never resolves against a
 * text/event-stream response that's designed to stay open. Wraps the native
 * EventSource directly; the /events route takes no auth today (see
 * docs/api-contracts.md), so no header/token plumbing is needed here.
 *
 * Returns an unsubscribe function, matching this codebase's existing
 * useEffect-cleanup idiom (e.g. FindingsPanel's `useEffect(() => {
 * void refresh(); }, [refresh])`).
 */
export function subscribeToWorkflowEvents(
  workflowId: string,
  onEvent: (event: WorkflowEvent) => void,
  onError?: (error: Event) => void,
  onOpen?: () => void
): () => void {
  const source = new EventSource(`${API_BASE_URL}/api/workflows/${workflowId}/events`);

  // The real signal that the SSE connection is live is the connection
  // itself opening - not "a message has arrived since mount". A workflow
  // that's already finished by the time a panel mounts (e.g. reloading the
  // page after completion) never sends another event, so relying on
  // onmessage alone left the "Connecting…" badge stuck forever even though
  // the stream was actually connected the whole time.
  if (onOpen) {
    source.onopen = onOpen;
  }

  source.onmessage = (message) => {
    try {
      onEvent(JSON.parse(message.data) as WorkflowEvent);
    } catch (error) {
      console.error("Failed to parse workflow event:", error);
    }
  };

  if (onError) {
    source.onerror = onError;
  }

  return () => source.close();
}
