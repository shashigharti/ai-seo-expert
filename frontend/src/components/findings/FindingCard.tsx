import { useState } from "react";
import { FINDING_STATUS_BADGE_CLASS, SEVERITY_BADGE_CLASS } from "../common/statusMaps";
import { humanizeAgentLabel } from "../common/textFormat";
import type { StoredFinding } from "../../features/findings/types";

interface FindingCardProps {
  storedFinding: StoredFinding;
  selected: boolean;
  onToggle: (id: string) => void;
}

/** docs/specs.md §2: expandable/collapsible per-issue detail, confidence
 * score, and references to authoritative sources. Implemented as a
 * Bootstrap-styled accordion item driven by local React state, rather than
 * pulling in Bootstrap's JS bundle (this app only ever loaded the CSS -
 * see main.tsx) for one component.
 *
 * No per-item margin or colored border here - Bootstrap's own
 * `.accordion-item:not(:first-of-type) { border-top: 0 }` already merges
 * stacked items into a single grouped list with hairline dividers; adding
 * `mb-2` + a colored left border (as this used to) defeats that and makes
 * every finding look like its own separate boxed card. Severity/status are
 * already conveyed by the two badges below, so the color bar was also
 * redundant, not just visually heavier than needed. */
export function FindingCard({ storedFinding, selected, onToggle }: FindingCardProps) {
  const { id, finding, status, agent_name } = storedFinding;
  const canSelect = status === "pending";
  const [expanded, setExpanded] = useState(false);

  return (
    <div className={`accordion-item ${selected ? "is-selected" : ""}`}>
      {/* h4, not h3 - FindingsPanel's per-agent group heading (the accordion's
       * own section heading, immediately above this <div className="accordion">)
       * is already an h3, so each individual item inside it must nest one
       * level below (h2 Findings > h3 agent group > h4 item), not repeat h3. */}
      <h4 className="accordion-header px-3 py-2">
        <div className="d-flex align-items-center gap-2">
          <div className="form-check mb-0">
            <input
              className="form-check-input"
              type="checkbox"
              id={`finding-${id}`}
              checked={selected}
              disabled={!canSelect}
              aria-label={`Select finding: ${finding.title}`}
              title={canSelect ? undefined : `Already ${status} - cannot be re-selected`}
              onChange={() => onToggle(id)}
            />
          </div>
          <button
            type="button"
            className={`accordion-button ${expanded ? "" : "collapsed"} py-2`}
            onClick={() => setExpanded((prev) => !prev)}
            aria-expanded={expanded}
          >
            <span className={`text-truncate ${selected ? "" : "fw-semibold"}`}>{finding.title}</span>
          </button>
        </div>
        {/* Severity/status on their own row below the title, indented past
         * the checkbox, instead of squeezed onto the title's own line. */}
        <div className="d-flex gap-2 mt-2 ps-4">
          <span className={`badge ${SEVERITY_BADGE_CLASS[finding.severity]}`}>{finding.severity}</span>
          <span className={`badge ${FINDING_STATUS_BADGE_CLASS[status]}`}>{status}</span>
        </div>
      </h4>
      <div className={`accordion-collapse collapse ${expanded ? "show" : ""}`}>
        <div className="accordion-body">
          <p className="text-secondary small mb-3">
            {finding.category} · found by {humanizeAgentLabel(agent_name)}
            {finding.confidence != null && ` · ${Math.round(finding.confidence * 100)}% confidence`}
          </p>
          <p className="mb-3">{finding.description}</p>
          <div className="finding-detail-grid mb-3">
            <div className="meta-item">
              <span className="meta-label">Evidence</span>
              <span>{finding.evidence}</span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Recommendation</span>
              <span>{finding.recommendation}</span>
            </div>
          </div>
          {finding.references.length > 0 && (
            <div className="meta-item">
              <span className="meta-label">References</span>
              <ul className="mb-0 small list-unstyled">
                {finding.references.map((url) => (
                  <li key={url} className="d-flex align-items-center gap-1">
                    <i className="bi bi-link-45deg text-secondary" aria-hidden="true" />
                    <a href={url} target="_blank" rel="noreferrer">
                      {url}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
