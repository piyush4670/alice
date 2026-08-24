"""The event bus.

One thread-safe bridge between worker threads (engine, conversation)
and every connected WebSocket. Events are dropped, never deadlocked:
a slow client loses polish, not the mission.
"""

import asyncio
import threading

MAX_QUEUE = 800


class EventBus:

    def __init__(self):

        self._loop = None
        self._queues = set()
        self._lock = threading.Lock()

    def bind(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    async def subscribe(self) -> asyncio.Queue:

        queue = asyncio.Queue(maxsize=MAX_QUEUE)

        with self._lock:
            self._queues.add(queue)

        return queue

    def unsubscribe(self, queue: asyncio.Queue):

        with self._lock:
            self._queues.discard(queue)

    def emit(self, event: dict):

        loop = self._loop

        if loop is None or loop.is_closed():
            return

        try:
            loop.call_soon_threadsafe(self._fanout, event)
        except RuntimeError:
            pass  # Loop shutting down during reload; the event is lost, not fatal.

    def _fanout(self, event: dict):

        with self._lock:
            queues = list(self._queues)

        for queue in queues:

            try:
                queue.put_nowait(event)

            except asyncio.QueueFull:

                # Shed the oldest event to keep the newest flowing.
                try:
                    queue.get_nowait()
                    queue.put_nowait(event)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    pass
