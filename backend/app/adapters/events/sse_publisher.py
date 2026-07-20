import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from uuid import UUID

from app.domain.models.event import WorkflowEvent


class SSEEventPublisher:
    """In-process adapter implementing the EventPublisher port.

    No external broker: subscribers are asyncio.Queue instances held in
    memory, keyed by workflow_id. Adequate for a single-process deployment
    (docs/architecture.md doesn't call for a message broker); a Redis-backed
    adapter could implement the same port later without changing callers.
    """

    def __init__(self) -> None:
        self._subscribers: dict[UUID, list[asyncio.Queue[WorkflowEvent]]] = defaultdict(list)

    async def publish(self, event: WorkflowEvent) -> None:
        for queue in self._subscribers.get(event.workflow_id, []):
            await queue.put(event)

    async def subscribe(self, workflow_id: UUID) -> AsyncIterator[WorkflowEvent]:
        queue: asyncio.Queue[WorkflowEvent] = asyncio.Queue()
        self._subscribers[workflow_id].append(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers[workflow_id].remove(queue)


# Single process-wide instance: publishers (orchestrator) and subscribers
# (SSE route) must share the same queues.
sse_event_publisher = SSEEventPublisher()
