import { useState } from "react";

interface ApprovalBarProps {
  selectedCount: number;
  isApproving: boolean;
  onApprove: (prStrategy: string) => void;
}

export function ApprovalBar({ selectedCount, isApproving, onApprove }: ApprovalBarProps) {
  const [prStrategy, setPrStrategy] = useState("by_category");

  return (
    <div className="pill-bar action-bar">
      <span className="me-auto d-flex align-items-center gap-1 small text-secondary" aria-live="polite">
        <i className="bi bi-check2-square" aria-hidden="true" />
        {selectedCount} selected
      </span>
      <select
        className="bare-control action-bar-select"
        value={prStrategy}
        onChange={(event) => setPrStrategy(event.target.value)}
        aria-label="Pull request strategy"
      >
        <option value="by_category">One PR per category</option>
        <option value="single">Single PR</option>
      </select>
      <button
        type="button"
        className="btn btn-success btn-sm rounded-pill d-inline-flex align-items-center gap-2"
        disabled={selectedCount === 0 || isApproving}
        onClick={() => onApprove(prStrategy)}
      >
        {isApproving ? (
          <span className="spinner-border spinner-border-sm" aria-hidden="true" />
        ) : (
          <i className="bi bi-check2-circle" aria-hidden="true" />
        )}
        {isApproving ? "Approving…" : "Approve selected"}
      </button>
    </div>
  );
}
