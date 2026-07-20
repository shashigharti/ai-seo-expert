from typing import Protocol
from uuid import UUID

from app.domain.models.approval import Approval
from app.domain.models.memory_entry import MemoryEntry
from app.domain.models.pull_request import PullRequestResult
from app.domain.models.stored_finding import StoredFinding
from app.domain.models.task import Task
from app.domain.models.user import User
from app.domain.models.workflow import Workflow


class WorkflowRepository(Protocol):
    """Port: persistence boundary for workflows.

    Domain and application code depend on this Protocol only - never on a
    concrete adapter (see docs/project-structure.md Boundary Rule).
    """

    async def create(self, workflow: Workflow) -> Workflow: ...

    async def get(self, workflow_id: UUID) -> Workflow | None: ...

    async def update(self, workflow: Workflow) -> Workflow: ...


class TaskRepository(Protocol):
    """Port: persistence boundary for tasks dispatched by the Orchestrator."""

    async def create(self, task: Task) -> Task: ...

    async def get(self, task_id: UUID) -> Task | None: ...

    async def update(self, task: Task) -> Task: ...

    async def list_for_workflow(self, workflow_id: UUID) -> list[Task]: ...


class ResultRepository(Protocol):
    """Port: persistence boundary for findings (docs/architecture.md §6
    Hexagonal Ports names this ResultRepository)."""

    async def save_many(self, findings: list[StoredFinding]) -> list[StoredFinding]: ...

    async def list_for_workflow(self, workflow_id: UUID) -> list[StoredFinding]: ...

    async def get_many(self, finding_ids: list[UUID]) -> list[StoredFinding]: ...

    async def mark_status(self, finding_ids: list[UUID], status: str) -> None: ...


class ApprovalRepository(Protocol):
    """Port: persistence boundary for the approval audit trail
    (docs/implementation.md Phase 7 "audit trail")."""

    async def create(self, approval: Approval) -> Approval: ...

    async def list_for_workflow(self, workflow_id: UUID) -> list[Approval]: ...


class PullRequestRepository(Protocol):
    """Port: persistence boundary for generated pull request results."""

    async def create(self, pull_request: PullRequestResult) -> PullRequestResult: ...

    async def list_for_workflow(self, workflow_id: UUID) -> list[PullRequestResult]: ...


class MemoryRepository(Protocol):
    """Port: persistence boundary for repository memory
    (docs/agent-architecture.md §12)."""

    async def add(self, entry: MemoryEntry) -> MemoryEntry: ...

    async def list_for_repository(self, repository_url: str) -> list[MemoryEntry]: ...

    async def delete_expired(self) -> int: ...


class UserRepository(Protocol):
    """Port: persistence boundary for user accounts (Phase 10 auth)."""

    async def create(self, user: User) -> User: ...

    async def get_by_email(self, email: str) -> User | None: ...

    async def get_by_id(self, user_id: UUID) -> User | None: ...
