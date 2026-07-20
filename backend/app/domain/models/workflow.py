from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.domain.enums.workflow_status import WorkflowStatus

# The UI no longer asks the user for a goal (see WorkflowForm) - the
# manager (agents/managers/seo_manager.py) still needs one to plan against,
# so every workflow gets this broad default instead. Its own SKILL.md says
# "only select capabilities that are actually relevant to the stated goal";
# a broad goal here is what makes it relevant-select all 5 capabilities,
# matching "find SEO issues" with no further narrowing from the user.
DEFAULT_GOAL = "Perform a full SEO, accessibility, and performance audit and identify all issues."


class Workflow(BaseModel):
    """Core domain representation of a workflow, independent of persistence."""

    id: UUID
    repository_url: str
    branch: str = "master"
    goal: str = DEFAULT_GOAL
    status: WorkflowStatus
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
