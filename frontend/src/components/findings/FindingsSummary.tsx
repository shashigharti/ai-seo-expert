import { SEVERITY_BADGE_CLASS } from "../common/statusMaps";
import type { FindingListResponse, Severity } from "../../features/findings/types";

interface FindingsSummaryProps {
  summary: FindingListResponse;
}

export function FindingsSummary({ summary }: FindingsSummaryProps) {
  return (
    <div className="findings-summary pb-3 mb-3 border-bottom">
      <div className="d-flex align-items-baseline gap-1">
        <span className="findings-summary-total">{summary.total}</span>
        <span className="text-secondary small">finding{summary.total === 1 ? "" : "s"}</span>
      </div>
      <div className="d-flex flex-wrap align-items-center gap-2 mt-2">
        {Object.entries(summary.findings_by_severity).map(([severity, count]) => (
          <span key={severity} className={`badge ${SEVERITY_BADGE_CLASS[severity as Severity]}`}>
            {severity}: {count}
          </span>
        ))}
      </div>
      <div className="d-flex flex-wrap align-items-center gap-2 mt-2">
        {Object.entries(summary.findings_by_category).map(([category, count]) => (
          <span key={category} className="badge text-bg-light border">
            {category}: {count}
          </span>
        ))}
      </div>
    </div>
  );
}
