import asyncio
import pytest
from feature_graph.core.engine.event_bus import EventBus, EventType


@pytest.mark.asyncio
async def test_subscribe_and_publish():
    bus = EventBus()
    received = []

    async def handler(payload):
        received.append(payload)

    bus.subscribe(EventType.REPOSITORY_INDEXED, handler)

    # start bus, publish, then stop
    task = asyncio.create_task(bus.start())
    await asyncio.sleep(0.05)
    await bus.publish(EventType.REPOSITORY_INDEXED, {"repo": "test"})
    await asyncio.sleep(0.1)
    await bus.stop()
    task.cancel()

    assert received == [{"repo": "test"}]


@pytest.mark.asyncio
async def test_multiple_handlers():
    bus = EventBus()
    calls = []

    async def h1(p): calls.append("h1")
    async def h2(p): calls.append("h2")

    bus.subscribe(EventType.GRAPH_REBUILT, h1)
    bus.subscribe(EventType.GRAPH_REBUILT, h2)

    task = asyncio.create_task(bus.start())
    await asyncio.sleep(0.05)
    await bus.publish(EventType.GRAPH_REBUILT, {})
    await asyncio.sleep(0.1)
    await bus.stop()
    task.cancel()

    assert "h1" in calls and "h2" in calls


@pytest.mark.asyncio
async def test_unsubscribe():
    bus = EventBus()
    calls = []

    async def handler(p): calls.append(p)

    bus.subscribe(EventType.COMMIT_DETECTED, handler)
    bus.unsubscribe(EventType.COMMIT_DETECTED, handler)

    task = asyncio.create_task(bus.start())
    await asyncio.sleep(0.05)
    await bus.publish(EventType.COMMIT_DETECTED, {"sha": "abc"})
    await asyncio.sleep(0.1)
    await bus.stop()
    task.cancel()

    assert calls == []
