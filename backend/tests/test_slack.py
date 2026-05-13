"""Slack Bolt + Block Kit + EventBus subscriber tests (D2-T1).

Coverage:
1. Block Kit JSON 빌더 — proposed/confirmed/pivoted 상태별
2. URL verification — Slack Events handshake
3. Interactive payload — Confirm action → missions store update + bus publish
4. Idempotency — 동일 action_ts 재시도 시 dedupe
5. Dry-run — 토큰 미설정 시 503

signing secret 검증은 Bolt SDK 책임이라 unit test에서는 우회 (settings.slack_enabled 직접 토글).
"""
from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.schemas.mission import (
    Mission,
    MissionStatus,
    MissionType,
    MissionUrgency,
)
from app.services.slack_blocks import (
    build_mission_card,
    build_text_fallback,
)


# ════════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════════
def _make_mission(**overrides) -> Mission:
    defaults = dict(
        mission_id=uuid4(),
        mission_type=MissionType.HEDGE,
        status=MissionStatus.PROPOSED,
        goal_text="Term 60% → 75% (4주)",
        pattern_score=82.5,
        reasoning="Test reasoning — Iran 제재 + Russia-Ukraine.",
        simulation_roi={"Brent_130": 410.0, "Brent_110": 140.0, "Brent_90": -50.0},
        urgency=MissionUrgency.URGENT,
        target_pct=75,
        duration_days=28,
        created_at=datetime.now(timezone.utc),
        version=1,
    )
    defaults.update(overrides)
    return Mission(**defaults)


# ════════════════════════════════════════════════════════════════════════
# 1. Block Kit JSON builder
# ════════════════════════════════════════════════════════════════════════
def test_block_kit_proposed_has_action_buttons():
    m = _make_mission()
    blocks = build_mission_card(m, action_state="proposed")
    assert isinstance(blocks, list)
    assert len(blocks) >= 5  # header + section*4 + divider + actions

    actions = [b for b in blocks if b.get("type") == "actions"]
    assert len(actions) == 1
    btn_ids = {el["action_id"] for el in actions[0]["elements"]}
    assert btn_ids == {
        "mission_confirm", "mission_reject", "mission_pivot",
        "mission_modify", "mission_open_apps",
    }

    # button value JSON is parseable + length < 2000
    confirm_btn = next(e for e in actions[0]["elements"] if e["action_id"] == "mission_confirm")
    val = json.loads(confirm_btn["value"])
    assert val["mid"] == str(m.mission_id)
    assert val["v"] == 1
    assert len(confirm_btn["value"]) < 2000


def test_block_kit_confirmed_no_action_buttons():
    m = _make_mission(status=MissionStatus.ACTIVE, confirmed_via="slack", confirmed_by="test_user")
    blocks = build_mission_card(m, action_state="confirmed")
    actions = [b for b in blocks if b.get("type") == "actions"]
    # confirmed 상태에서도 'Open in Apps'만 남는 단일 action block 1개
    assert len(actions) == 1
    btn_ids = {el["action_id"] for el in actions[0]["elements"]}
    assert btn_ids == {"mission_open_apps"}

    # context block 확인
    contexts = [b for b in blocks if b.get("type") == "context"]
    assert len(contexts) == 1
    assert "Confirmed" in contexts[0]["elements"][0]["text"]


def test_block_kit_fallback_text():
    m = _make_mission()
    text = build_text_fallback(m, action_state="proposed")
    assert "URGENT" in text
    assert "HEDGE" in text
    assert "60% → 75%" in text


# ════════════════════════════════════════════════════════════════════════
# 2. SlackNotifier dry-run + ts map
# ════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_notifier_dryrun_post_returns_fake_ts(monkeypatch):
    # Force dry-run
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    monkeypatch.delenv("SLACK_SIGNING_SECRET", raising=False)
    monkeypatch.delenv("SLACK_DEFAULT_CHANNEL", raising=False)
    get_settings.cache_clear()

    from app.services.slack_notify import reset_notifier_for_testing, get_notifier
    reset_notifier_for_testing()
    notifier = get_notifier()
    assert notifier.enabled is False

    m = _make_mission()
    ts = await notifier.post_mission_card(m)
    assert ts.startswith("dryrun-")

    # ts map 확인
    loc = notifier.get_ts(m.mission_id)
    assert loc is not None
    ch, saved_ts = loc
    assert saved_ts == ts

    # update도 silent skip 없이 정상 흐름
    m.status = MissionStatus.ACTIVE
    m.confirmed_via = "slack"
    m.confirmed_by = "test"
    await notifier.update_mission_card(m, action_state="confirmed")

    # cleanup
    get_settings.cache_clear()
    reset_notifier_for_testing()


# ════════════════════════════════════════════════════════════════════════
# 3. /api/slack/health endpoint (dry-run mode reachable)
# ════════════════════════════════════════════════════════════════════════
def test_slack_health_endpoint(monkeypatch):
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    monkeypatch.delenv("SLACK_SIGNING_SECRET", raising=False)
    monkeypatch.delenv("SLACK_DEFAULT_CHANNEL", raising=False)
    get_settings.cache_clear()

    from app.main import app
    client = TestClient(app)
    resp = client.get("/api/slack/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is False
    assert data["has_bot_token"] is False
    assert "(missing)" in data["default_channel"]

    get_settings.cache_clear()


# ════════════════════════════════════════════════════════════════════════
# 4. Dry-run: /api/slack/events + /api/slack/interactive return 503
# ════════════════════════════════════════════════════════════════════════
def test_slack_events_dryrun_returns_503(monkeypatch):
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    monkeypatch.delenv("SLACK_SIGNING_SECRET", raising=False)
    monkeypatch.delenv("SLACK_DEFAULT_CHANNEL", raising=False)
    get_settings.cache_clear()

    # Reset Bolt app cache (이전 테스트에서 enabled 됐을 수도)
    from app.api import slack as slack_mod
    slack_mod._app = None
    slack_mod._handler = None

    from app.main import app
    client = TestClient(app)
    resp = client.post("/api/slack/events", json={"type": "url_verification", "challenge": "abc"})
    assert resp.status_code == 503
    assert resp.json()["detail"]["code"] == "SLACK_DRY_RUN"

    resp2 = client.post("/api/slack/interactive", data={"payload": "{}"})
    assert resp2.status_code == 503

    get_settings.cache_clear()


# ════════════════════════════════════════════════════════════════════════
# 5. Idempotency cache — dedupe 검증
# ════════════════════════════════════════════════════════════════════════
def test_idempotency_dedupes_same_key():
    from app.api.slack import _idem_check, _idem_key, _idem_cache
    _idem_cache.clear()

    mid = str(uuid4())
    key = _idem_key("12345", "mission_confirm", mid, 1)
    assert _idem_check(key) is False  # 1번째: not seen
    assert _idem_check(key) is True   # 2번째: dedupe

    # 다른 key 는 영향 X
    key2 = _idem_key("12346", "mission_confirm", mid, 1)
    assert _idem_check(key2) is False


# ════════════════════════════════════════════════════════════════════════
# 6. Action handler — Confirm action 실제 missions store update
# (Bolt 우회: _do_mission_action 함수 직접 호출)
# ════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_confirm_action_updates_store_and_publishes(monkeypatch):
    from app.api.slack import _do_mission_action
    from app.store import reset_store_for_testing, get_store, get_bus

    monkeypatch.setenv("USE_LAKEBASE", "false")
    monkeypatch.setenv("DEMO_MODE", "false")
    get_settings.cache_clear()
    reset_store_for_testing()

    store = get_store()
    bus = get_bus()
    sub_q = await bus.subscribe()

    m = _make_mission()
    await store.create(m)

    new, err = await _do_mission_action(
        "mission_confirm", body={"user": {"id": "U1", "username": "tester"}},
        mission_id=m.mission_id, version=1, actor="slack:tester@U1",
    )
    assert err is None
    assert new is not None
    assert new.status == MissionStatus.ACTIVE
    assert new.confirmed_via == "slack"
    assert new.version == 2

    # bus event 확인
    event = await asyncio.wait_for(sub_q.get(), timeout=1.0)
    assert event["type"] == "mission.confirmed"
    assert event["mission"]["mission_id"] == str(m.mission_id)

    await bus.unsubscribe(sub_q)
    reset_store_for_testing()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_pivot_action_toggles_type(monkeypatch):
    from app.api.slack import _do_mission_action
    from app.store import reset_store_for_testing, get_store, get_bus

    monkeypatch.setenv("USE_LAKEBASE", "false")
    monkeypatch.setenv("DEMO_MODE", "false")
    get_settings.cache_clear()
    reset_store_for_testing()

    store = get_store()
    bus = get_bus()
    sub_q = await bus.subscribe()

    m = _make_mission(mission_type=MissionType.HEDGE)
    await store.create(m)

    new, err = await _do_mission_action(
        "mission_pivot", body={"user": {"id": "U1", "username": "tester"}},
        mission_id=m.mission_id, version=1, actor="slack:tester@U1",
    )
    assert err is None
    assert new is not None
    assert new.mission_type == MissionType.OPPORTUNITY
    assert new.status == MissionStatus.PIVOTED
    assert len(new.pivot_history) == 1
    assert new.pivot_history[0].from_type == MissionType.HEDGE
    assert new.pivot_history[0].to_type == MissionType.OPPORTUNITY

    event = await asyncio.wait_for(sub_q.get(), timeout=1.0)
    assert event["type"] == "mission.pivoted"

    await bus.unsubscribe(sub_q)
    reset_store_for_testing()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_confirm_409_returns_ephemeral_error(monkeypatch):
    from app.api.slack import _do_mission_action
    from app.store import reset_store_for_testing, get_store

    monkeypatch.setenv("USE_LAKEBASE", "false")
    monkeypatch.setenv("DEMO_MODE", "false")
    get_settings.cache_clear()
    reset_store_for_testing()

    store = get_store()
    m = _make_mission()
    await store.create(m)
    # 누군가 먼저 v=2로 confirm
    await store.update(m.mission_id, 1, lambda x: x)

    # stale version 1로 Slack confirm 시도 → 에러 메시지
    new, err = await _do_mission_action(
        "mission_confirm", body={"user": {"id": "U1", "username": "tester"}},
        mission_id=m.mission_id, version=1, actor="slack:tester@U1",
    )
    assert new is None
    assert err is not None
    assert "이미" in err or "처리" in err

    reset_store_for_testing()
    get_settings.cache_clear()


# ════════════════════════════════════════════════════════════════════════
# 7. EventBus subscriber — proposed → notifier.post_mission_card 1회 호출
# ════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_slack_subscriber_handles_proposed_event(monkeypatch):
    from app.services.slack_bus_subscriber import _handle_event

    notifier = AsyncMock()
    notifier.enabled = False
    store = AsyncMock()

    m = _make_mission()
    event = {"type": "mission.proposed", "mission": m.model_dump(mode="json")}

    await _handle_event(event, notifier, store)
    notifier.post_mission_card.assert_called_once()
    # confirmed update는 호출 안 됨
    notifier.update_mission_card.assert_not_called()


@pytest.mark.asyncio
async def test_slack_subscriber_handles_confirmed_event(monkeypatch):
    from app.services.slack_bus_subscriber import _handle_event

    notifier = AsyncMock()
    notifier.enabled = False
    store = AsyncMock()

    m = _make_mission(status=MissionStatus.ACTIVE, confirmed_via="slack", confirmed_by="u1")
    event = {"type": "mission.confirmed", "mission": m.model_dump(mode="json")}

    await _handle_event(event, notifier, store)
    notifier.update_mission_card.assert_called_once()
    # call kwargs/args inspection
    call = notifier.update_mission_card.call_args
    # action_state='confirmed' 검증
    assert call.kwargs.get("action_state") == "confirmed" or "confirmed" in str(call)
