export type WorkflowStepStatus = "done" | "current" | "upcoming";

export interface WorkflowStep {
  label: string;
  status: WorkflowStepStatus;
}

/** Results page process guide: "Search -> Approve -> Generate Pull
 * Request". Each step's status is derived from real workflow/findings/
 * pull-request state by the caller (DashboardPage) - not a static
 * decoration, an actual reflection of where this run has really gotten to. */
export function WorkflowSteps({ steps }: { steps: WorkflowStep[] }) {
  return (
    <ol className="workflow-steps list-unstyled d-flex mb-0">
      {steps.map((step, index) => (
        <li
          key={step.label}
          className={`workflow-step is-${step.status}`}
          aria-current={step.status === "current" ? "step" : undefined}
        >
          <span className="workflow-step-marker" aria-hidden="true">
            {step.status === "done" ? <i className="bi bi-check-lg" /> : index + 1}
          </span>
          <span className="workflow-step-label">{step.label}</span>
        </li>
      ))}
    </ol>
  );
}
