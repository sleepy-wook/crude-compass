"""In-memory mission store + WebSocket event bus.

Sprint 4: 데모 시연용 단순 dict store. Sprint 5 또는 데모 후 Lakebase로 swap.
- get_pool() (db/lakebase.py)이 정의되어 있어 추후 swap easy
- thread-safe asyncio.Lock 사용
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.schemas.mission import (
    Mission,
    MissionStatus,
    MissionType,
    MissionUrgency,
    PivotEntry,
)


class MissionStore:
    """In-memory mission store with optimistic concurrency (version field)."""

    def __init__(self):
        self._missions: dict[UUID, Mission] = {}
        self._lock = asyncio.Lock()

    async def create(self, mission: Mission) -> Mission:
        async with self._lock:
            self._missions[mission.mission_id] = mission
            return mission

    async def get(self, mission_id: UUID) -> Mission | None:
        async with self._lock:
            return self._missions.get(mission_id)

    async def get_active(self) -> list[Mission]:
        """proposed + active + on_track + at_risk + paused."""
        active_statuses = {
            MissionStatus.PROPOSED,
            MissionStatus.ACTIVE,
            MissionStatus.ON_TRACK,
            MissionStatus.AT_RISK,
            MissionStatus.PAUSED,
        }
        async with self._lock:
            return [
                m for m in self._missions.values()
                if m.status in active_statuses
            ]

    async def update(
        self,
        mission_id: UUID,
        expected_version: int,
        updater,
    ) -> Mission | None:
        """Optimistic update. Returns None if version mismatch.

        updater: callable(Mission) -> Mission — must return new mission instance.
        """
        async with self._lock:
            m = self._missions.get(mission_id)
            if m is None:
                return None
            if m.version != expected_version:
                return None  # caller handles 409
            new = updater(m)
            new.version = m.version + 1
            self._missions[mission_id] = new
            return new

    async def all(self) -> list[Mission]:
        async with self._lock:
            return list(self._missions.values())


# Singleton instance
_store: MissionStore | None = None


def get_store() -> MissionStore:
    global _store
    if _store is None:
        _store = MissionStore()
        # seed with 1 demo mission for Sprint 4 quick start
        _seed_demo(_store)
    return _store


def _seed_demo(store: MissionStore) -> None:
    """Seed 1 sample mission for empty-state UX testing (sync helper)."""
    demo = Mission(
        mission_id=uuid4(),
        mission_type=MissionType.HEDGE,
        status=MissionStatus.PROPOSED,
        goal_text="Pre-emptive HEDGE: Term 75% → 90% (4주)",
        pattern_score=82.0,
        reasoning="호르무즈 위기 누적 — Iran 제재 + Russia-Ukraine + UK Maritime alerts. AI confidence 78%.",
        simulation_roi={"Brent_130_봉쇄": 410.0, "Brent_110_긴장": 140.0, "Brent_90_평화": -50.0},
        urgency=MissionUrgency.URGENT,
        target_pct=90,
        duration_days=28,
        created_at=datetime.now(timezone.utc),
        version=1,
    )
    store._missions[demo.mission_id] = demo


# ════════════════════════════════════════════════════════════════════════
# WebSocket event bus — pub/sub broadcasting
# ════════════════════════════════════════════════════════════════════════
class EventBus:
    """Simple in-process pub/sub for WebSocket broadcast.

    SLA: server-side event emit ~ all client receive < 1s.
    """

    def __init__(self):
        self._subscribers: set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue:
        """Returns a fresh queue that receives all events."""
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        async with self._lock:
            self._subscribers.add(q)
        return q

    async def unsubscribe(self, q: asyncio.Queue) -> None:
        async with self._lock:
            self._subscribers.discard(q)

    async def publish(self, event: dict) -> None:
        """Broadcast event to all subscribers (drop if full)."""
        async with self._lock:
            subs = list(self._subscribers)
        for q in subs:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass


_bus: EventBus | None = None


def get_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus
