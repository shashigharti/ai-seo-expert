import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { AgentExecutionPanel } from "../components/agentExecution/AgentExecutionPanel";
import { GitHubPRExecutionPanel } from "../components/agentExecution/GitHubPRExecutionPanel";
import { FeatureCard } from "../components/common/FeatureCard";
import { FindingsPanel } from "../components/findings/FindingsPanel";
import { PullRequestPanel } from "../components/pullRequests/PullRequestPanel";
import { WorkflowForm } from "../components/workflow/WorkflowForm";
import { WorkflowStatusCard } from "../components/workflow/WorkflowStatusCard";
import type { WorkflowStep } from "../components/workflow/WorkflowSteps";
import { WorkflowSteps } from "../components/workflow/WorkflowSteps";
import { useWorkflow } from "../features/workflows/useWorkflow";

const FEATURE_HIGHLIGHTS = [
  {
    icon: "bi-lightning-charge",
    title: "Fast Scans",
    description: "Discover SEO issues in seconds.",
  },
  {
    icon: "bi-check2-circle",
    title: "Actionable Fixes",
    description: "Know exactly what to fix.",
  },
  {
    icon: "bi-stopwatch",
    title: "Time Saving",
    description: "Spend less time auditing and more time growing.",
  },
];

const DEMO_REPOSITORY_URL = "https://github.com/shashigharti/ai-seo-test";

const ROADMAP_ITEMS = [
  "Let anyone scan and fix any GitHub repository, not just the demo one below.",
  "GitHub sign-in, so each user connects their own account instead of sharing one server-side token.",
  "Per-user GitHub access tokens, scoped to only the repositories that user approves.",
];

/** docs/specs.md's two-column layout: left is the primary content
 * (progress/status, results, fix actions), right is the live Agent
 * Execution Panel. No inline CSS (docs/system-design.md §2).
 *
 * The scan input is a chat-style composer (WorkflowForm) that starts
 * vertically centered on the page - no result to show yet - and slides to
 * the top the moment a scan starts, making room for the results below. The
 * slide is driven by `.composer-shell`/`.composer-docked` in styles/index.css
 * transitioning the shell's min-height down to nothing: as free space
 * shrinks, centering itself carries the bar upward, no drag/JS animation
 * needed. Once a scan has started it stays docked - there's no reason to
 * float the composer back to center after showing a result or error.
 *
 * The current workflow's id lives in the URL (/workflows/:workflowId) -
 * without that, a browser refresh always reset back to the blank composer,
 * since useWorkflow's state starts empty on every fresh page load and
 * nothing else remembered which workflow was showing. */
export function DashboardPage() {
  const { workflowId: routeWorkflowId } = useParams<{ workflowId?: string }>();
  const navigate = useNavigate();
  const { workflow, isLoading, error, submit, load } = useWorkflow();
  // The pr_strategy findings were actually approved with - passed to
  // PullRequestPanel so "Generate Pull Request(s)" uses what was really
  // chosen in ApprovalBar, not a separately hardcoded default.
  const [approvedStrategy, setApprovedStrategy] = useState("by_category");
  // Real progress signals for the WorkflowSteps guide below - each only
  // flips once something has actually happened (an approval succeeded, a
  // real PullRequestResult exists), not just "the relevant panel rendered".
  const [hasApprovedFindings, setHasApprovedFindings] = useState(false);
  const [hasGeneratedPullRequest, setHasGeneratedPullRequest] = useState(false);

  // A direct visit to /workflows/:id (a bookmark, or reloading the results
  // page) needs to actually fetch that workflow.
  useEffect(() => {
    if (routeWorkflowId && workflow?.id !== routeWorkflowId) {
      void load(routeWorkflowId);
    }
  }, [routeWorkflowId, workflow?.id, load]);

  // Keep the URL in sync with whichever workflow is actually showing, so a
  // freshly submitted scan becomes bookmarkable/refreshable too.
  useEffect(() => {
    if (workflow && workflow.id !== routeWorkflowId) {
      navigate(`/workflows/${workflow.id}`);
    }
  }, [workflow, routeWorkflowId, navigate]);

  const hasStarted = isLoading || workflow !== null || error !== null || Boolean(routeWorkflowId);

  const workflowSteps: WorkflowStep[] | null = workflow && [
    {
      label: "Search",
      status: workflow.status === "pending" || workflow.status === "running" ? "current" : "done",
    },
    {
      label: "Approve",
      status: hasApprovedFindings ? "done" : workflow.status === "completed" ? "current" : "upcoming",
    },
    {
      label: "Generate Pull Request",
      status: hasGeneratedPullRequest ? "done" : hasApprovedFindings ? "current" : "upcoming",
    },
  ];

  return (
    <div className="container py-5">
      <div className={`composer-shell ${hasStarted ? "composer-docked" : ""}`}>
        {!hasStarted && (
          <div className="text-center mb-4">
            <h1 className="h3 mb-2">Find SEO issues in your website</h1>
            <p className="text-secondary mb-4">
              Get a full SEO audit in seconds, powered by five specialized AI agents. See{" "}
              <Link to="/about">About</Link> for how it works.
            </p>
            <div className="row row-cols-1 row-cols-md-3 g-3 text-start mb-4">
              {FEATURE_HIGHLIGHTS.map((feature) => (
                <FeatureCard key={feature.title} titleAs="h2" {...feature} />
              ))}
            </div>
          </div>
        )}
        <WorkflowForm
          onSubmit={submit}
          isSubmitting={isLoading}
          initialRepositoryUrl={workflow?.repository_url}
          initialBranch={workflow?.branch}
        />
      </div>

      {/* Hackathon-submission context: which repo this build actually
       * demos against, and what's intentionally out of scope for now (see
       * ROADMAP_ITEMS above) - shown alongside the feature highlights, not
       * inside .composer-shell, so it doesn't affect the composer's own
       * vertical-centering math. */}
      {!hasStarted && (
        <div className="row row-cols-1 row-cols-md-2 g-4 mt-4">
          <div className="col">
            <div className="card h-100 p-4 shadow-sm">
              <h2 className="h6 d-flex align-items-center gap-2">
                <i className="bi bi-github text-primary" aria-hidden="true" />
                Test repository
              </h2>
              <p className="text-secondary small mb-2">
                Want to see the whole pipeline in action, PR included? Point a scan at:
              </p>
              <p className="mb-2">
                <strong>Test Repository:</strong>{" "}
                <a href={DEMO_REPOSITORY_URL} target="_blank" rel="noreferrer">
                  {DEMO_REPOSITORY_URL}
                </a>
              </p>
              <p className="text-secondary small mb-0">
                Any public GitHub repository can be scanned, and will get real SEO findings back.
                Actually opening a pull request, though, needs write access to the target
                repository - and that's currently only set up for the repository above. Use it to
                walk through everything end-to-end: scanning, findings, and automated pull-request
                generation.
              </p>
            </div>
          </div>
          <div className="col">
            <div className="card h-100 p-4 shadow-sm">
              <h2 className="h6 d-flex align-items-center gap-2">
                <i className="bi bi-signpost-2 text-primary" aria-hidden="true" />
                Roadmap
              </h2>
              <ul className="text-secondary small mb-0 ps-3">
                {ROADMAP_ITEMS.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {hasStarted && (
        <>
          {workflowSteps && (
            <div className="d-flex justify-content-center mt-4">
              <WorkflowSteps steps={workflowSteps} />
            </div>
          )}

          <div className="row g-4 mt-1">
            <div className="col-lg-7">
              {isLoading && !workflow && !error && (
                <p className="text-secondary d-flex align-items-center gap-2">
                  <span className="spinner-border spinner-border-sm" aria-hidden="true" />
                  Loading workflow…
                </p>
              )}

              {error && (
                <div className="alert alert-danger" role="alert">
                  {error}
                </div>
              )}

              {workflow && (
                <>
                  <WorkflowStatusCard workflow={workflow} />
                  <div className="mt-4">
                    <FindingsPanel
                      workflowId={workflow.id}
                      workflowStatus={workflow.status}
                      onApproved={setApprovedStrategy}
                      onApprovalStateChange={setHasApprovedFindings}
                    />
                  </div>
                  <div className="mt-4">
                    <PullRequestPanel
                      workflowId={workflow.id}
                      defaultStrategy={approvedStrategy}
                      onGenerated={() => setHasGeneratedPullRequest(true)}
                    />
                  </div>
                </>
              )}
            </div>

            <div className="col-lg-5">
              {workflow && (
                <div className="sticky-top sticky-offset-top">
                  <AgentExecutionPanel workflowId={workflow.id} />
                  <div className="mt-4">
                    <GitHubPRExecutionPanel workflowId={workflow.id} />
                  </div>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
