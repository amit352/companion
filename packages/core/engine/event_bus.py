import asyncio
from collections import defaultdict
from enum import StrEnum
from typing import Any, Callable, Coroutine

import structlog

log = structlog.get_logger()


class EventType(StrEnum):
    REPOSITORY_INDEXED = "repository.indexed"
    COMMIT_DETECTED = "repository.commit_detected"
    FEATURE_UPDATED = "graph.feature_updated"
    GRAPH_REBUILT = "graph.rebuilt"
    PLUGIN_REGISTERED = "plugin.registered"
    PLUGIN_FAILED = "plugin.failed"
    ANALYSIS_STARTED = "analysis.started"
    ANALYSIS_COMPLETED = "analysis.completed"


Handler = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


class EventBus:
    """Async pub/sub event bus for plugin-to-engine communication."""

    def __init__(self) -> None:
        self._handlers: dict[EventType, list[Handler]] = defaultdict(list)
        self._queue: asyncio.Queue[tuple[EventType, dict[str, Any]]] = asyncio.Queue()
        self._running = False

    def subscribe(self, event_type: EventType, handler: Handler) -> None:
        self._handlers[event_type].append(handler)
        log.debug("event_subscribed", event=event_type, handler=handler.__qualname__)

    def unsubscribe(self, event_type: EventType, handler: Handler) -> None:
        self._handlers[event_type].remove(handler)

    async def publish(self, event_type: EventType, payload: dict[str, Any]) -> None:
        await self._queue.put((event_type, payload))

    async def start(self) -> None:
        self._running = True
        log.info("event_bus_started")
        while self._running:
            try:
                event_type, payload = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                handlers = self._handlers.get(event_type, [])
                await asyncio.gather(
                    *[h(payload) for h in handlers],
                    return_exceptions=True,
                )
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue

    async def stop(self) -> None:
        self._running = False
        log.info("event_bus_stopped")
