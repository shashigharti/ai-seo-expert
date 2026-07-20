import { StatusBadge } from "../common/StatusBadge";
import { PULL_REQUEST_STATUS_BADGE_CLASS } from "../common/statusMaps";
import type { PullRequestResult } from "../../features/pullRequests/types";

interface PullRequestResultCardProps {
  result: PullRequestResult;
}

/** A plain `.list-row` rather than its own `.card` - see
 * AgentExecutionCard for why (already inside PullRequestPanel's card). */
export function PullRequestResultCard({ result }: PullRequestResultCardProps) {
  return (
    <div className="list-row">
      <div className="d-flex justify-content-between align-items-start">
        <h3 className="h6 mb-2">{result.commit_summary}</h3>
        <StatusBadge status={result.status} classMap={PULL_REQUEST_STATUS_BADGE_CLASS} />
      </div>
      <div className="meta-grid">
        <div className="meta-item">
          <span className="meta-label">Repository</span>
          <span className="meta-value">{result.repository_url}</span>
        </div>
        <div className="meta-item">
          <span className="meta-label">Branch</span>
          <code className="meta-value">{result.branch_name}</code>
        </div>
        {result.status === "opened" && result.url && (
          <div className="meta-item">
            <span className="meta-label">Pull Request</span>
            <a href={result.url} target="_blank" rel="noreferrer" className="d-inline-flex align-items-center gap-1">
              <span className="meta-value">{result.url}</span>
              <i className="bi bi-box-arrow-up-right flex-shrink-0" aria-hidden="true" />
            </a>
          </div>
        )}
        {result.status === "failed" && result.error_message && (
          <div className="meta-item">
            <span className="meta-label">Error</span>
            <span className="meta-value text-danger d-flex align-items-center gap-1">
              <i className="bi bi-exclamation-triangle flex-shrink-0" aria-hidden="true" />
              {result.error_message}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
