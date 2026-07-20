import { getRequest, postRequest } from "../../services/apiClient";
import type { CreateWorkflowInput, Workflow } from "./types";

export function createWorkflow(input: CreateWorkflowInput): Promise<Workflow> {
  return postRequest<Workflow>("/api/workflows", input);
}

export function getWorkflow(workflowId: string): Promise<Workflow> {
  return getRequest<Workflow>(`/api/workflows/${workflowId}`);
}
