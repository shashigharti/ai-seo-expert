export type Severity = "low" | "medium" | "high" | "critical";
export type FindingStatus = "pending" | "approved" | "rejected";

export interface Finding {
  category: string;
  severity: Severity;
  title: string;
  description: string;
  evidence: string;
  recommendation: string;
  references: string[];
  confidence: number | null;
}

export interface StoredFinding {
  id: string;
  workflow_id: string;
  task_id: string;
  agent_name: string;
  finding: Finding;
  status: FindingStatus;
  created_at: string;
}

export interface FindingListResponse {
  total: number;
  findings_by_category: Record<string, number>;
  findings_by_severity: Record<string, number>;
  items: StoredFinding[];
}

export interface ApprovalResponse {
  id: string;
  workflow_id: string;
  finding_ids: string[];
  pr_strategy: string;
  created_at: string;
}
