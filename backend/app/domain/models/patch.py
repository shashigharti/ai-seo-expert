from uuid import UUID

from pydantic import BaseModel


class ProposedPatch(BaseModel):
    """One file's proposed fix. Whole-file replacement, not a line-level
    diff - simpler and more reliable for an LLM to produce correctly than a
    unified diff, at the cost of noisier commits; a deliberate scope choice
    for this phase, not an oversight.
    """

    file_path: str
    new_content: str
    commit_message: str


class FixGroup(BaseModel):
    """One group of approved findings to be fixed together in one PR,
    per the workflow's `pr_strategy` (docs/api-contracts.md).
    """

    label: str
    finding_ids: list[UUID]


class FixPlan(BaseModel):
    """A Fix Manager's plan for one FixGroup: branch, PR title/body, and the
    patches a Fix Worker produced for it.
    """

    branch_name: str
    pr_title: str
    pr_body: str
    finding_ids: list[UUID]
    patches: list[ProposedPatch]
