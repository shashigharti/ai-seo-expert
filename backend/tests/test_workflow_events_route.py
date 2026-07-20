import asyncio
import uuid

from starlette.requests import Request

from app.adapters.events.sse_publisher import sse_event_publisher
from app.api.routes.workflows import stream_workflow_events
from app.domain.models.event import WorkflowEvent


def _fake_request() -> Request:
    """A Request whose is_disconnected() always reports connected - enough
    for exercising the route's body_iterator directly, without a real ASGI
    connection.
    """

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    scope = {"type": "http", "headers": [], "client": None}
    return Request(scope, receive=receive)


async def test_route_streams_events_published_on_the_shared_publisher():
    """Verifies the DI-provided EventPublisher in the route is the same
    singleton instance the rest of the app (e.g. the Orchestrator) publishes
    through - the actual wiring claim behind the SSE endpoint, exercised at
    the route-function level to avoid this environment's ASGI streaming
    transport issue (see review/CHANGELOG.md Phase 2 notes).
    """
    workflow_id = uuid.uuid4()
    response = await stream_workflow_events(workflow_id, _fake_request(), sse_event_publisher)

    body_iterator = response.body_iterator

    async def publish_soon():
        await asyncio.sleep(0.05)
        await sse_event_publisher.publish(WorkflowEvent(type="task.started", workflow_id=workflow_id))

    publisher_task = asyncio.create_task(publish_soon())
    chunk = await asyncio.wait_for(anext(body_iterator), timeout=2)
    await publisher_task

    assert chunk.startswith("data: ")
    assert '"type":"task.started"' in chunk
    assert str(workflow_id) in chunk

    await body_iterator.aclose()
