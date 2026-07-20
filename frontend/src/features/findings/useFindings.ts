import { useCallback, useState } from "react";
import { ApiError } from "../../services/apiClient";
import { approveFindings, getFindings } from "./api";
import type { ApprovalResponse, FindingListResponse } from "./types";

interface UseFindingsState {
  data: FindingListResponse | null;
  isLoading: boolean;
  error: string | null;
}

export function useFindings(workflowId: string) {
  const [state, setState] = useState<UseFindingsState>({ data: null, isLoading: false, error: null });
  const [isApproving, setIsApproving] = useState(false);

  const refresh = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      const data = await getFindings(workflowId);
      setState({ data, isLoading: false, error: null });
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Failed to load findings";
      setState({ data: null, isLoading: false, error: message });
    }
  }, [workflowId]);

  const approve = useCallback(
    async (findingIds: string[], prStrategy: string): Promise<ApprovalResponse> => {
      setIsApproving(true);
      try {
        const response = await approveFindings(workflowId, findingIds, prStrategy);
        await refresh();
        return response;
      } finally {
        setIsApproving(false);
      }
    },
    [workflowId, refresh],
  );

  return { ...state, isApproving, refresh, approve };
}
