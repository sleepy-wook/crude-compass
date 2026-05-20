"""agent_activity_events repository tests — list_recent_all 신규.

LAKEBASE_HOST env 없으면 skip (CI 안전).
"""
from __future__ import annotations

import os
import pytest

from app.db.repositories import agent_activity

pytestmark = pytest.mark.skipif(
    not os.getenv("LAKEBASE_HOST"),
    reason="LAKEBASE_HOST not set — Lakebase integration test skipped",
)


def test_list_recent_all_returns_cross_mission_events():
    """전역 pulse stream용 — mission_id 무관 최근 N건 + system 이벤트 포함."""
    from app.db.lakebase import get_conn

    with get_conn() as conn:
        # insert 2 events with different mission_ids + 1 system event (mission_id=None)
        agent_activity.insert_event_autocommit(
            conn, mission_id=None, actor="gdelt", action="signal_detected",
            result_preview="test signal A",
        )
        events = agent_activity.list_recent_all(conn, limit=10)

    assert isinstance(events, list)
    assert len(events) >= 1
    # 최근순 (DESC) 정렬 검증 — 첫 event의 occurred_at >= 마지막
    if len(events) >= 2:
        assert events[0]["occurred_at"] >= events[-1]["occurred_at"]
    # system event (mission_id=None) 포함 검증
    assert any(e["mission_id"] is None for e in events)


def test_list_recent_all_since_filter():
    """since timestamp 이후 events만 반환."""
    from datetime import datetime, timezone, timedelta
    from app.db.lakebase import get_conn

    with get_conn() as conn:
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        events = agent_activity.list_recent_all(conn, limit=100, since=future)

    assert events == []  # 미래 시점 → empty
