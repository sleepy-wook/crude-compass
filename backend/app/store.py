"""In-process pub/sub event bus — Live AI Pulse 전용.

mission store/event bus는 reports 모델 전환으로 제거됨.
pulse bus만 잔존: agent_activity_events INSERT 시 broadcast → /api/ws/pulse.
"""
from __future__ import annotations

import asyncio


# ════════════════════════════════════════════════════════════════════════
# WebSocket event bus — in-process pub/sub
# ════════════════════════════════════════════════════════════════════════
class EventBus:
    """Simple in-process pub/sub for WebSocket broadcast.

    SLA: server-side event emit ~ all client receive < 1s.
    """

    def __init__(self):
        self._subscribers: set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        async with self._lock:
            self._subscribers.add(q)
        return q

    async def unsubscribe(self, q: asyncio.Queue) -> None:
        async with self._lock:
            self._subscribers.discard(q)

    async def publish(self, event: dict) -> None:
        async with self._lock:
            subs = list(self._subscribers)
        for q in subs:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass


_pulse_bus: EventBus | None = None


def get_pulse_bus() -> EventBus:
    """Live AI Pulse 전용 bus — agent_activity_events INSERT 시 broadcast.

    전역 AI activity (cron, supervisor) 전부 받음. /api/ws/pulse 가 구독.
    """
    global _pulse_bus
    if _pulse_bus is None:
        _pulse_bus = EventBus()
    return _pulse_bus
