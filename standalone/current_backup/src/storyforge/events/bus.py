"""
In-process publish/subscribe over asyncio.Queue.

Each subscriber gets their own queue. publish() fans out to every queue
without blocking the publisher. Slow subscribers don't block fast ones —
queues are unbounded by default; if you ever need backpressure, swap to
asyncio.Queue(maxsize=N) and decide on a drop policy.

Aether integration point: subscribe a queue here to feed StoryForge
events into the IPCBus.
"""
from __future__ import annotations
import asyncio
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._lock = asyncio.Lock()
    
    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        """Register a new subscriber and return its receive queue."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._subscribers.add(queue)
        return queue
    
    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self._subscribers.discard(queue)
    
    async def publish(self, message: dict[str, Any]) -> None:
        """Fan out a message to every subscriber. Non-blocking per consumer."""
        async with self._lock:
            targets = list(self._subscribers)
        for q in targets:
            # put_nowait would raise QueueFull on bounded queues; we use
            # unbounded queues so this never blocks.
            q.put_nowait(message)


# Module-level singleton — one bus per process.
event_bus = EventBus()
