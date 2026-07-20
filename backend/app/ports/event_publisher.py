from collections.abc import AsyncIterator
from typing import Protocol
from uuid import UUID

from app.domain.models.event import WorkflowEvent


class EventPublisher(Protocol):
    """Port: publish/subscribe boundary for workflow progress events."""

    async def publish(self, event: WorkflowEvent) -> None: ...

    def subscribe(self, workflow_id: UUID) -> AsyncIterator[WorkflowEvent]: ...
