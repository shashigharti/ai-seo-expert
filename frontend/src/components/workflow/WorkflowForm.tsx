import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import type { CreateWorkflowInput } from "../../features/workflows/types";

interface WorkflowFormProps {
  onSubmit: (input: CreateWorkflowInput) => Promise<boolean>;
  isSubmitting: boolean;
  /** The active workflow's repository URL/branch, if one exists - pre-fills
   * (and keeps showing) it instead of a blank box. Covers both landing
   * directly on /workflows/:id (a refresh or bookmark - DashboardPage's
   * `load()`) and having just submitted a scan, so the box always reflects
   * what's actually showing rather than resetting itself. */
  initialRepositoryUrl?: string;
  initialBranch?: string;
}

const BRANCH_PRESETS = ["master", "main", "develop"];
const CUSTOM_BRANCH_VALUE = "__custom__";

/** A single-row "composer" bar (URL input + branch dropdown + send button)
 * in place of a stacked form - docs/specs.md's "minimize unnecessary
 * clicks" principle, styled after chat-style input bars (ChatGPT/Claude).
 * Branch is a dropdown of common presets rather than a plain text field,
 * with a "Custom…" option that swaps in a free-text input for anything
 * else, since branch names aren't a fixed small set. */
export function WorkflowForm({ onSubmit, isSubmitting, initialRepositoryUrl, initialBranch }: WorkflowFormProps) {
  const [repositoryUrl, setRepositoryUrl] = useState(initialRepositoryUrl ?? "");
  const [branch, setBranch] = useState(initialBranch ?? "master");
  const [isCustomBranch, setIsCustomBranch] = useState(
    initialBranch != null && !BRANCH_PRESETS.includes(initialBranch)
  );

  // `initialRepositoryUrl`/`initialBranch` arrive asynchronously (the
  // workflow load resolves after mount on a direct /workflows/:id visit),
  // so the useState defaults above alone only cover the case where they're
  // already known at mount time - this effect re-syncs once they resolve.
  useEffect(() => {
    if (initialRepositoryUrl !== undefined) setRepositoryUrl(initialRepositoryUrl);
  }, [initialRepositoryUrl]);

  useEffect(() => {
    if (initialBranch !== undefined) {
      setBranch(initialBranch);
      setIsCustomBranch(!BRANCH_PRESETS.includes(initialBranch));
    }
  }, [initialBranch]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await onSubmit({
      repository_url: repositoryUrl,
      branch: branch.trim() || "master",
    });
    // No longer clearing the input on success - the box should keep
    // showing the URL of whatever workflow is now active (see the
    // initialRepositoryUrl sync above), not reset to blank.
  };

  const handleBranchSelect = (value: string) => {
    if (value === CUSTOM_BRANCH_VALUE) {
      setIsCustomBranch(true);
      setBranch("");
    } else {
      setBranch(value);
    }
  };

  const handleCustomBranchBlur = () => {
    if (!branch.trim()) {
      setBranch("master");
      setIsCustomBranch(false);
    }
  };

  return (
    <form className="pill-bar composer-bar" onSubmit={handleSubmit}>
      <i className="bi bi-github text-secondary flex-shrink-0 ms-1" aria-hidden="true" />
      <input
        type="url"
        className="bare-control composer-input"
        placeholder="Paste a GitHub repository URL to scan for SEO issues…"
        value={repositoryUrl}
        onChange={(event) => setRepositoryUrl(event.target.value)}
        aria-label="Repository URL"
        required
      />

      <div className="composer-divider" aria-hidden="true" />

      {isCustomBranch ? (
        <input
          type="text"
          className="bare-control composer-branch-input"
          value={branch}
          onChange={(event) => setBranch(event.target.value)}
          onBlur={handleCustomBranchBlur}
          placeholder="branch"
          aria-label="Branch name"
          autoFocus
        />
      ) : (
        <select
          className="bare-control composer-branch-select"
          value={branch}
          onChange={(event) => handleBranchSelect(event.target.value)}
          aria-label="Branch"
        >
          {BRANCH_PRESETS.map((preset) => (
            <option key={preset} value={preset}>
              {preset}
            </option>
          ))}
          <option value={CUSTOM_BRANCH_VALUE}>Custom…</option>
        </select>
      )}

      <button
        type="submit"
        className="composer-submit"
        disabled={isSubmitting}
        aria-label={isSubmitting ? "Starting scan…" : "Start scan"}
      >
        {isSubmitting ? (
          <span className="spinner-border spinner-border-sm" aria-hidden="true" />
        ) : (
          <i className="bi bi-arrow-up" aria-hidden="true" />
        )}
      </button>
    </form>
  );
}
