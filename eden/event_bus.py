"""Thread-safe EventBus — bridges sync reconciler thread to async SSE streams.

Publish from any thread. Subscribe from async SSE handlers.
"""

from __future__ import annotations

import asyncio
import queue
import threading
import time

import structlog

logger = structlog.get_logger(__name__)


class EventBus:
    """Thread-safe pub/sub for real-time event streaming.

    - publish() is safe to call from any thread (reconciler, agent, MQTT)
    - subscribe() returns a thread-safe queue for SSE consumers
    - Keeps a rolling history so new subscribers get recent context
    """

    def __init__(self, history_size: int = 200) -> None:
        self._subscribers: list[queue.Queue] = []
        self._lock = threading.Lock()
        self._history: list[dict] = []
        self._history_size = history_size
        self._event_count = 0

    def publish(self, event_type: str, data: dict | list | str | None = None) -> None:
        """Publish an event from any thread."""
        event = {
            "type": event_type,
            "data": data if data is not None else {},
            "timestamp": time.time(),
            "seq": self._event_count,
        }
        self._event_count += 1

        with self._lock:
            self._history.append(event)
            if len(self._history) > self._history_size:
                self._history = self._history[-self._history_size:]

            for q in self._subscribers:
                try:
                    q.put_nowait(event)
                except queue.Full:
                    # Slow consumer — drop oldest events
                    try:
                        q.get_nowait()
                        q.put_nowait(event)
                    except (queue.Empty, queue.Full):
                        pass

    def subscribe(self, max_size: int = 500) -> queue.Queue:
        """Create a new subscriber queue. Thread-safe."""
        q: queue.Queue = queue.Queue(maxsize=max_size)
        with self._lock:
            self._subscribers.append(q)
        logger.debug("subscriber_added", total_subscribers=len(self._subscribers))
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        """Remove a subscriber queue."""
        with self._lock:
            self._subscribers = [s for s in self._subscribers if s is not q]
        logger.debug("subscriber_removed", total_subscribers=len(self._subscribers))

    def get_history(self, event_type: str | None = None, limit: int = 50) -> list[dict]:
        """Get recent events from history. Optionally filter by type."""
        with self._lock:
            if event_type:
                filtered = [e for e in self._history if e["type"] == event_type]
                return filtered[-limit:]
            return list(self._history[-limit:])

    @property
    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subscribers)

    @property
    def event_count(self) -> int:
        return self._event_count
