import { useEffect, useRef } from "react";
import { PullRequestResultCard } from "./PullRequestResultCard";
import { usePullRequests } from "../../features/pullRequests/usePullRequests";

interface PullRequestPanelProps {
  workflowId: string;
  /** The pr_strategy the findings were actually approved with (see
   * FindingsPanel's onApproved) - generation should use the same strategy
   * that was approved, not a separately hardcoded default. */
  defaultStrategy?: string;
  /** Fired once the first real PullRequestResult appears (this workflow's
   * `results` going from empty to non-empty) - lets DashboardPage's
   * WorkflowSteps mark "Generate Pull Request" done from a real signal
   * (a result actually exists), not just "the button was clicked". */
  onGenerated?: () => void;
}

export function PullRequestPanel({ workflowId, defaultStrategy = "by_category", onGenerated }: PullRequestPanelProps) {
  const { results, isGenerating, error, generate } = usePullRequests(workflowId);

  const hasNotifiedGenerated = useRef(false);
  useEffect(() => {
    if (results.length > 0 && !hasNotifiedGenerated.current) {
      hasNotifiedGenerated.current = true;
      onGenerated?.();
    }
  }, [results.length, onGenerated]);

  return (
    <div className="card p-4 shadow-sm">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h2 className="h5 mb-0 d-flex align-items-center gap-2">
          <i className="bi bi-git text-primary" aria-hidden="true" />
          Pull Requests
        </h2>
        <button
          type="button"
          className="btn btn-primary btn-sm rounded-pill d-inline-flex align-items-center gap-2"
          disabled={isGenerating}
          onClick={() => void generate(defaultStrategy)}
        >
          {isGenerating ? (
            <span className="spinner-border spinner-border-sm" aria-hidden="true" />
          ) : (
            <i className="bi bi-magic" aria-hidden="true" />
          )}
          {isGenerating ? "Generating…" : "Generate Pull Request(s)"}
        </button>
      </div>

      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}

      {results.length === 0 && !isGenerating && !error && (
        <p className="text-secondary mb-0 d-flex align-items-center gap-2">
          <i className="bi bi-info-circle" aria-hidden="true" />
          Approve findings above, then generate a pull request for the fixes.
        </p>
      )}

      {results.map((result) => (
        <PullRequestResultCard key={result.id} result={result} />
      ))}
    </div>
  );
}
