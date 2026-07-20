import asyncio
import uuid

from app.adapters.events.sse_publisher import SSEEventPublisher
from app.domain.models.event import WorkflowEvent


async def test_subscriber_receives_published_events_in_order():
    publisher = SSEEventPublisher()
    workflow_id = uuid.uuid4()

    subscription = publisher.subscribe(workflow_id)
    first = asyncio.create_task(anext(subscription))
    await asyncio.sleep(0.05)  # let the subscriber register before publishing

    await publisher.publish(WorkflowEvent(type="task.started", workflow_id=workflow_id))
    await publisher.publish(WorkflowEvent(type="task.completed", workflow_id=workflow_id))

    received_first = await first
    received_second = await anext(subscription)

    assert received_first.type == "task.started"
    assert received_second.type == "task.completed"


async def test_events_for_other_workflows_are_not_delivered():
    publisher = SSEEventPublisher()
    workflow_id = uuid.uuid4()
    other_workflow_id = uuid.uuid4()

    subscription = publisher.subscribe(workflow_id)
    pending = asyncio.create_task(anext(subscription))
    await asyncio.sleep(0.05)

    await publisher.publish(WorkflowEvent(type="task.started", workflow_id=other_workflow_id))
    await publisher.publish(WorkflowEvent(type="task.started", workflow_id=workflow_id))

    received = await asyncio.wait_for(pending, timeout=1)
    assert received.workflow_id == workflow_id


async def test_multiple_subscribers_each_receive_the_event():
    publisher = SSEEventPublisher()
    workflow_id = uuid.uuid4()

    sub_a = publisher.subscribe(workflow_id)
    sub_b = publisher.subscribe(workflow_id)
    task_a = asyncio.create_task(anext(sub_a))
    task_b = asyncio.create_task(anext(sub_b))
    await asyncio.sleep(0.05)

    await publisher.publish(WorkflowEvent(type="task.completed", workflow_id=workflow_id))

    result_a, result_b = await asyncio.gather(task_a, task_b)
    assert result_a.type == "task.completed"
    assert result_b.type == "task.completed"


async def test_cancelling_the_subscriber_removes_its_queue():
    publisher = SSEEventPublisher()
    workflow_id = uuid.uuid4()

    subscription = publisher.subscribe(workflow_id)
    consumer = asyncio.create_task(anext(subscription))
    await asyncio.sleep(0.05)  # let it register and block on queue.get()
    assert len(publisher._subscribers[workflow_id]) == 1

    consumer.cancel()
    try:
        await consumer
    except asyncio.CancelledError:
        pass

    assert len(publisher._subscribers[workflow_id]) == 0
