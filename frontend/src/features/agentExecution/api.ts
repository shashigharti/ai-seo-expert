import { getRequest } from "../../services/apiClient";
import type { TaskExecutionListResponse } from "./types";

export function getTasks(workflowId: string): Promise<TaskExecutionListResponse> {
  return getRequest<TaskExecutionListResponse>(`/api/workflows/${workflowId}/tasks`);
}
