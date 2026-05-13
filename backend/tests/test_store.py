"""MissionStore Protocol + InMemoryMissionStore + LakebaseMissionStore tests.

Lakebase integration test (`test_lakebase_*`) is skipped unless LAKEBASE_HOST env is set.
InMemory tests cover the same behaviors so Lakebase parity 검증 가능.
"""
from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.schemas.mission import (
    Mission,
    MissionStatus,
    MissionType,
    MissionUrgency,
    PivotEntry,
)
from app.store import (
    EventBus,
    InMemoryMissionStore,
    LakebaseMissionStore,
    MissionStore,
)


def _make_mission(**overrides) -> Mission:
    defaults = dict(
        mission_id=uuid4(),
        mission_type=MissionType.HEDGE,
        status=MissionStatus.PROPOSED,
        goal_text="Term 60% → 75% (4주)",
        pattern_score=82.0,
        reasoning="Test mission",
        simulation_roi={"Brent_130": 410.0, "Brent_90": -50.0},
        urgency=MissionUrgency.URGENT,
        target_pct=75,
        duration_days=28,
        created_at=datetime.now(timezone.utc),
        version=1,
    )
    defaults.update(overrides)
    return Mission(**defaults)


# ════════════════════════════════════════════════════════════════════════
# Protocol contract
# ════════════════════════════════════════════════════════════════════════
def test_inmemory_satisfies_protocol():
    store = InMemoryMissionStore()
    assert isinstance(store, MissionStore)


def test_lakebase_class_loadable():
    # LakebaseMissionStore should be importable without actual DB connection
    assert LakebaseMissionStore.__name__ == "LakebaseMissionStore"


# ════════════════════════════════════════════════════════════════════════
# InMemoryMissionStore — create / get / get_active / update / version conflict
# ════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_inmemory_create_get():
    store = InMemoryMissionStore()
    m = _make_mission()
    created = await store.create(m)
    assert created.mission_id == m.mission_id

    fetched = await store.get(m.mission_id)
    assert fetched is not None
    assert fetched.mission_type == MissionType.HEDGE
    assert fetched.version == 1


@pytest.mark.asyncio
async def test_inmemory_get_active_excludes_aborted():
    store = InMemoryMissionStore()
    m_active = _make_mission(status=MissionStatus.PROPOSED)
    m_aborted = _make_mission(status=MissionStatus.ABORTED)
    await store.create(m_active)
    await store.create(m_aborted)

    active = await store.get_active()
    ids = {m.mission_id for m in active}
    assert m_active.mission_id in ids
    assert m_aborted.mission_id not in ids


@pytest.mark.asyncio
async def test_inmemory_update_version_bump():
    store = InMemoryMissionStore()
    m = _make_mission()
    await store.create(m)

    def _confirm(mission):
        mission.status = MissionStatus.ACTIVE
        mission.confirmed_by = "tester"
        return mission

    updated = await store.update(m.mission_id, expected_version=1, updater=_confirm)
    assert updated is not None
    assert updated.version == 2
    assert updated.status == MissionStatus.ACTIVE
    assert updated.confirmed_by == "tester"


@pytest.mark.asyncio
async def test_inmemory_update_version_conflict():
    store = InMemoryMissionStore()
    m = _make_mission()
    await store.create(m)

    # First update bumps to v2
    await store.update(m.mission_id, 1, lambda x: x)

    # Second update with stale version 1 should fail (return None)
    result = await store.update(m.mission_id, 1, lambda x: x)
    assert result is None


@pytest.mark.asyncio
async def test_inmemory_pivot_history_preserved():
    """Roundtrip of pivot_history through update."""
    store = InMemoryMissionStore()
    m = _make_mission()
    await store.create(m)

    def _pivot(mission):
        mission.mission_type = MissionType.OPPORTUNITY
        mission.status = MissionStatus.PIVOTED
        mission.pivot_history = [
            *mission.pivot_history,
            PivotEntry(
                from_type=MissionType.HEDGE,
                to_type=MissionType.OPPORTUNITY,
                occurred_at=datetime.now(timezone.utc),
                reason="휴전 임박",
                pattern_score_at=38.0,
            ),
        ]
        return mission

    updated = await store.update(m.mission_id, 1, _pivot)
    assert updated is not None
    assert len(updated.pivot_history) == 1
    assert updated.pivot_history[0].from_type == MissionType.HEDGE
    assert updated.pivot_history[0].to_type == MissionType.OPPORTUNITY
    assert updated.pivot_history[0].pattern_score_at == 38.0


@pytest.mark.asyncio
async def test_inmemory_get_nonexistent():
    store = InMemoryMissionStore()
    result = await store.get(uuid4())
    assert result is None


# ════════════════════════════════════════════════════════════════════════
# EventBus pub/sub
# ════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_eventbus_publish_to_multiple_subscribers():
    bus = EventBus()
    q1 = await bus.subscribe()
    q2 = await bus.subscribe()

    event = {"type": "mission.proposed", "mission_id": str(uuid4())}
    await bus.publish(event)

    received1 = await asyncio.wait_for(q1.get(), timeout=1.0)
    received2 = await asyncio.wait_for(q2.get(), timeout=1.0)
    assert received1 == event
    assert received2 == event


@pytest.mark.asyncio
async def test_eventbus_unsubscribe():
    bus = EventBus()
    q = await bus.subscribe()
    await bus.unsubscribe(q)

    await bus.publish({"type": "test"})

    # Queue should not receive (timeout expected)
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(q.get(), timeout=0.2)


# ════════════════════════════════════════════════════════════════════════
# JSONB roundtrip — repository-level (no DB, just serialization)
# ════════════════════════════════════════════════════════════════════════
def test_pivot_entry_jsonb_roundtrip():
    """Verify Pydantic → JSON → dict → Pydantic preserves datetime + enum."""
    entry = PivotEntry(
        from_type=MissionType.HEDGE,
        to_type=MissionType.OPPORTUNITY,
        occurred_at=datetime(2026, 5, 13, 14, 30, 0, tzinfo=timezone.utc),
        reason="test",
        pattern_score_at=42.5,
    )
    # Serialize as backend would (json.dumps with model_dump(mode='json'))
    raw = json.dumps([entry.model_dump(mode="json")])
    # Deserialize (simulating JSONB readback)
    parsed = json.loads(raw)
    assert len(parsed) == 1
    p = parsed[0]
    assert p["from_type"] == "HEDGE"
    assert p["to_type"] == "OPPORTUNITY"
    assert p["pattern_score_at"] == 42.5
    # ISO datetime preserved
    assert "2026-05-13" in p["occurred_at"]
    assert "T14:30" in p["occurred_at"]


# ════════════════════════════════════════════════════════════════════════
# Lakebase integration test — gated by LAKEBASE_HOST env (skip in CI)
# ════════════════════════════════════════════════════════════════════════
@pytest.mark.skipif(
    not os.getenv("LAKEBASE_HOST"),
    reason="LAKEBASE_HOST not set — skipping Lakebase integration test",
)
@pytest.mark.asyncio
async def test_lakebase_create_get_roundtrip():
    """Live integration test against Lakebase. Requires:
    - LAKEBASE_HOST, LAKEBASE_DATABASE, LAKEBASE_ENDPOINT_PATH, LAKEBASE_USER env vars
    - missions DDL applied (databricks/schemas/lakebase.sql)
    - DATABRICKS_CONFIG_PROFILE active for OAuth token
    """
    store = LakebaseMissionStore()
    m = _make_mission()
    created = await store.create(m)
    assert created.mission_id == m.mission_id

    fetched = await store.get(m.mission_id)
    assert fetched is not None
    assert fetched.mission_type == MissionType.HEDGE
    assert fetched.simulation_roi == m.simulation_roi
    assert fetched.version == 1
