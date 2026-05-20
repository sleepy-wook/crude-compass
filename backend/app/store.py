"""Mission store + WebSocket event bus.

Pluggable backends:
- InMemoryMissionStore (dev/demo default, dict)
- LakebaseMissionStore (production, psycopg pool)

선택은 USE_LAKEBASE env var (true → Lakebase, 그 외 → in-memory).
"""
from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable
from uuid import UUID, uuid4

from app.schemas.mission import (
    Mission,
    MissionStatus,
    MissionType,
    MissionUrgency,
)


# ════════════════════════════════════════════════════════════════════════
# Protocol — all stores must implement these
# ════════════════════════════════════════════════════════════════════════
@runtime_checkable
class MissionStore(Protocol):
    async def create(self, mission: Mission) -> Mission: ...
    async def get(self, mission_id: UUID) -> Mission | None: ...
    async def get_active(self) -> list[Mission]: ...
    async def all(self) -> list[Mission]: ...
    async def update(
        self, mission_id: UUID, expected_version: int, updater
    ) -> Mission | None: ...


# ════════════════════════════════════════════════════════════════════════
# In-memory store (dev/demo default)
# ════════════════════════════════════════════════════════════════════════
class InMemoryMissionStore:
    """Dict-backed store. asyncio.Lock for concurrency safety."""

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
        active_statuses = {
            MissionStatus.PROPOSED, MissionStatus.ACTIVE,
            MissionStatus.ON_TRACK, MissionStatus.AT_RISK, MissionStatus.PAUSED,
        }
        async with self._lock:
            return [m for m in self._missions.values() if m.status in active_statuses]

    async def all(self) -> list[Mission]:
        async with self._lock:
            return list(self._missions.values())

    async def update(self, mission_id, expected_version, updater):
        async with self._lock:
            m = self._missions.get(mission_id)
            if m is None or m.version != expected_version:
                return None
            new = updater(m)
            new.version = m.version + 1
            self._missions[mission_id] = new
            return new


# ════════════════════════════════════════════════════════════════════════
# Lakebase store (production, psycopg pool)
# ════════════════════════════════════════════════════════════════════════
class LakebaseMissionStore:
    """Postgres-backed store via psycopg pool.

    DDL: databricks/schemas/lakebase.sql
    Repository: app/db/repositories/missions.py
    Sync DB calls wrapped in asyncio.to_thread (psycopg async는 추후 옵션).
    """

    def __init__(self):
        # Lazy import to avoid forcing Lakebase config on InMemory deployments
        from app.db import lakebase as _lakebase
        from app.db.repositories import missions as _repo
        self._lakebase = _lakebase
        self._repo = _repo

    async def _run(self, fn, *args, **kwargs):
        """Acquire connection from pool + run sync fn in thread."""
        def _sync():
            with self._lakebase.acquire() as conn:
                return fn(conn, *args, **kwargs)
        return await asyncio.to_thread(_sync)

    async def create(self, mission: Mission) -> Mission:
        return await self._run(self._repo.insert, mission)

    async def get(self, mission_id: UUID) -> Mission | None:
        return await self._run(self._repo.get, mission_id)

    async def get_active(self) -> list[Mission]:
        return await self._run(self._repo.list_active)

    async def all(self) -> list[Mission]:
        return await self._run(self._repo.list_all)

    async def update(self, mission_id, expected_version, updater):
        """Lakebase update — applies updater to current mission then dispatches
        to the correct repository method based on status delta.

        This generic interface keeps API routers (missions.py) backend-agnostic.
        """
        # Strategy: load current, apply updater in memory, write via repo according to changed fields.
        # 단순화: API routers (confirm/reject/pivot/modify) 직접 호출 가능한 method 분리도 향후.
        current = await self.get(mission_id)
        if current is None or current.version != expected_version:
            return None

        # Run updater synchronously to compute the new mission shape
        new = updater(current.model_copy(deep=True))

        # Determine which repo function to call by diff
        if new.status == MissionStatus.ACTIVE and current.status != MissionStatus.ACTIVE:
            return await self._run(
                self._repo.confirm, mission_id, expected_version,
                new.confirmed_by or "system", new.confirmed_via or "apps",
            )
        if new.status == MissionStatus.ABORTED and current.status != MissionStatus.ABORTED:
            return await self._run(
                self._repo.reject, mission_id, expected_version,
                new.confirmed_by or "system", new.confirmed_via or "apps",
            )
        if new.status == MissionStatus.PIVOTED or new.mission_type != current.mission_type:
            # detect pivot — new entry was appended
            reason = "(no reason supplied)"
            to_type = new.mission_type.value
            if len(new.pivot_history) > len(current.pivot_history):
                p = new.pivot_history[-1]
                reason = p.reason
                to_type = p.to_type.value
            return await self._run(
                self._repo.pivot, mission_id, expected_version,
                "pivot", to_type, reason,
            )
        if new.status == MissionStatus.PAUSED and current.status != MissionStatus.PAUSED:
            return await self._run(
                self._repo.pivot, mission_id, expected_version, "pause", None, "manual pause",
            )
        # otherwise — modify (target_pct or duration_days)
        if new.target_pct != current.target_pct or new.duration_days != current.duration_days:
            return await self._run(
                self._repo.modify, mission_id, expected_version,
                new.target_pct, new.duration_days,
            )
        # no detectable change — return current
        return current


# ════════════════════════════════════════════════════════════════════════
# Backend selection — USE_LAKEBASE env flag
# ════════════════════════════════════════════════════════════════════════
_store: MissionStore | None = None


def _build_store() -> MissionStore:
    use_lakebase = os.getenv("USE_LAKEBASE", "false").lower() == "true"
    if use_lakebase:
        # 시도 — Lakebase pool init은 lazy라 init 자체는 fail 안 함.
        # 실제 connection fail은 첫 query 시점에 발견됨 (별도 health check 권장).
        try:
            lb_store: MissionStore = LakebaseMissionStore()
            # Smoke test — pool acquire 1회 시도 (10s timeout) → fail 시 fallback
            import logging as _logging
            from app.db.lakebase import acquire as _lb_acquire
            try:
                with _lb_acquire() as _conn:
                    with _conn.cursor() as _cur:
                        _cur.execute("SELECT 1")
                        _cur.fetchone()
                _logging.getLogger(__name__).info("Lakebase smoke test PASS — using LakebaseMissionStore")
                # Lakebase seed/cleanup: placeholder data 제거 + 한글 Bidirectional seed insert
                if os.getenv("DEMO_MODE", "true").lower() == "true":
                    _seed_demo_in_lakebase()
                return lb_store
            except Exception as e:
                _logging.getLogger(__name__).warning(
                    "Lakebase smoke test FAIL (%s) — falling back to InMemoryMissionStore + demo seed",
                    e,
                )
        except Exception as e:
            import logging as _logging
            _logging.getLogger(__name__).warning(
                "LakebaseMissionStore init failed (%s) — falling back to in-memory", e
            )
    in_mem = InMemoryMissionStore()
    if os.getenv("DEMO_MODE", "true").lower() == "true":
        _seed_demo_in_memory(in_mem)
    return in_mem


def _seed_demo_in_lakebase() -> None:
    """Lakebase missions table에 한글 Bidirectional seed 자동 적용.

    배경 (D-0 design review): Lakebase live화 후 PG에 placeholder data
    ("Term 60% → 75%" + "Test mission" + 둘 다 HEDGE) 잔존 → Bidirectional
    차별화 anchor 깨짐. 자동 cleanup + 한글 seed insert.

    조건:
    1. proposed 상태 mission이 0건이면 → 한글 seed 2개 INSERT
    2. proposed 상태 mission이 있는데 goal_text에 "Term " (영문 placeholder) 포함
       또는 reasoning == "Test mission" → 모두 ABORTED 처리 + 한글 seed 2개 INSERT

    실패해도 backend startup은 진행 (warning만 log).
    """
    import logging as _logging
    log = _logging.getLogger(__name__)
    try:
        from app.db.lakebase import acquire as _lb_acquire
        with _lb_acquire() as conn:
            with conn.cursor() as cur:
                # 1. 현재 proposed missions 검사
                cur.execute(
                    """
                    SELECT mission_id, goal_text, reasoning
                    FROM missions
                    WHERE status = 'proposed'
                    """
                )
                rows = cur.fetchall()
                placeholder_ids = [
                    r[0] for r in rows
                    if ("Term " in (r[1] or "") and "장기계약" not in (r[1] or ""))
                    or (r[2] or "").strip().lower() == "test mission"
                ]
                # 2. Placeholder는 ABORTED 처리 (audit log 유지, list에서 제외)
                if placeholder_ids:
                    cur.execute(
                        "UPDATE missions SET status = 'aborted' WHERE mission_id = ANY(%s)",
                        (placeholder_ids,),
                    )
                    log.info(
                        "Lakebase seed cleanup: %d placeholder missions → aborted",
                        len(placeholder_ids),
                    )
                # 3. 한글 seed가 이미 있는지 확인 — % escape: psycopg parameter placeholder 충돌 방지
                cur.execute(
                    "SELECT COUNT(*) FROM missions "
                    "WHERE status = 'proposed' "
                    "AND (goal_text LIKE %s OR goal_text LIKE %s)",
                    ('사전 위험방어%', '사전 기회포착%'),
                )
                ko_count = cur.fetchone()[0]
                if ko_count >= 2:
                    log.info("Lakebase seed: 한글 Bidirectional missions already present (n=%d), skip", ko_count)
                    conn.commit()
                    return
                # 4. 한글 Bidirectional seed insert
                now = datetime.now(timezone.utc)
                hedge_id = uuid4()
                opp_id = uuid4()
                cur.execute(
                    """
                    INSERT INTO missions (
                        mission_id, mission_type, status, goal_text, pattern_score,
                        reasoning, simulation_roi, urgency, target_pct, duration_days,
                        created_at, pivot_history, version
                    ) VALUES
                    (%s, 'HEDGE', 'proposed',
                     '사전 위험방어 — 장기계약 비중 60% → 75% (4주)', 82.0,
                     '호르무즈 위기 누적 — 이란 제재 + 러시아·우크라이나 + UK 해상 경보. AI 자신감 78%.',
                     %s::jsonb, 'urgent', 75, 28, %s, '[]'::jsonb, 1),
                    (%s, 'OPPORTUNITY', 'proposed',
                     '사전 기회포착 — 즉시구매 비중 40% → 55% (4주)', 22.0,
                     '약세 신호 누적 — 중국 PMI 49.2 (수요 둔화) + OECD 재고 증가 +280k/주 + 사우디 OSP $1.20 인하 (아시아향). 평시 미세 조정 기회. AI 자신감 64%.',
                     %s::jsonb, 'default', 55, 28, %s, '[]'::jsonb, 1)
                    """,
                    (
                        hedge_id,
                        json.dumps({"Brent_130_봉쇄": 410.0, "Brent_110_긴장": 140.0, "Brent_90_평화": -50.0}),
                        now,
                        opp_id,
                        json.dumps({"Brent_70_약세": 280.0, "Brent_80_안정": 90.0, "Brent_95_반등": -120.0}),
                        now,
                    ),
                )
                conn.commit()
                log.info("Lakebase seed inserted: 2 한글 Bidirectional missions (HEDGE + OPP)")
    except Exception as e:
        log.warning("Lakebase seed failed (non-blocking): %s", e)


def get_store() -> MissionStore:
    global _store
    if _store is None:
        _store = _build_store()
    return _store


def reset_store_for_testing() -> None:
    """Test helper — re-builds store from env."""
    global _store
    _store = None


def _seed_demo_in_memory(store: InMemoryMissionStore) -> None:
    """Seed 2 demo missions — Bidirectional 양방향 narrative (HEDGE + OPP).

    시나리오 §6 Bidirectional 차별화 anchor: 위기(HEDGE)와 기회(OPP) 동시 demo.
    """
    hedge = Mission(
        mission_id=uuid4(),
        mission_type=MissionType.HEDGE,
        status=MissionStatus.PROPOSED,
        goal_text="사전 위험방어 — 장기계약 비중 60% → 75% (4주)",
        pattern_score=82.0,
        reasoning="호르무즈 위기 누적 — 이란 제재 + 러시아·우크라이나 + UK 해상 경보. AI 자신감 78%.",
        simulation_roi={"Brent_130_봉쇄": 410.0, "Brent_110_긴장": 140.0, "Brent_90_평화": -50.0},
        urgency=MissionUrgency.URGENT,
        target_pct=75,
        duration_days=28,
        created_at=datetime.now(timezone.utc),
        version=1,
    )
    opp = Mission(
        mission_id=uuid4(),
        mission_type=MissionType.OPPORTUNITY,
        status=MissionStatus.PROPOSED,
        goal_text="사전 기회포착 — 즉시구매 비중 40% → 55% (4주)",
        pattern_score=22.0,
        reasoning=(
            "약세 신호 누적 — 중국 PMI 49.2 (수요 둔화) + OECD 재고 증가 +280k/주 + "
            "사우디 OSP $1.20 인하 (아시아향). 평시 미세 조정 기회. AI 자신감 64%."
        ),
        simulation_roi={"Brent_70_약세": 280.0, "Brent_80_안정": 90.0, "Brent_95_반등": -120.0},
        urgency=MissionUrgency.DEFAULT,
        target_pct=55,
        duration_days=28,
        created_at=datetime.now(timezone.utc),
        version=1,
    )
    store._missions[hedge.mission_id] = hedge
    store._missions[opp.mission_id] = opp


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


_bus: EventBus | None = None


def get_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus


_pulse_bus: EventBus | None = None


def get_pulse_bus() -> EventBus:
    """Live AI Pulse 전용 bus — agent_activity_events INSERT 시 broadcast.

    missions bus와 분리 — pulse client는 mission lifecycle만 받지 않고
    전역 AI activity (cron, supervisor, reactive) 전부 받음.
    """
    global _pulse_bus
    if _pulse_bus is None:
        _pulse_bus = EventBus()
    return _pulse_bus
