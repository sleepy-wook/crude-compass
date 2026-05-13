"""Demo inject endpoint tests (D2-T2).

Coverage:
1. DEMO_MODE=false → router 자체 mount 안 됨 → 404
2. hormuz_blockade preset → HEDGE/URGENT/Score 82 + Term 60%→75% goal_text 정확
3. ceasefire preset → OPPORTUNITY
4. custom scenario without required fields → 422
5. inject → EventBus 'mission.proposed' event 발행
6. 연속 inject 2건 → 별도 mission_id (intentionally non-idempotent)
"""
from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings


def _make_client_with_demo(enabled: bool, monkeypatch) -> TestClient:
    """DEMO_MODE 토글 후 새 app instance."""
    if enabled:
        monkeypatch.setenv("DEMO_MODE", "true")
    else:
        monkeypatch.setenv("DEMO_MODE", "false")
    get_settings.cache_clear()

    # Re-build app — main.py 의 create_app() 다시 호출하여 conditional mount 반영
    from app.main import create_app
    from app.store import reset_store_for_testing
    reset_store_for_testing()
    app = create_app()
    return TestClient(app)


# ════════════════════════════════════════════════════════════════════════
# 1. DEMO_MODE=false → 404
# ════════════════════════════════════════════════════════════════════════
def test_demo_disabled_returns_404(monkeypatch):
    client = _make_client_with_demo(False, monkeypatch)
    resp = client.post("/api/demo/inject_signal", json={"scenario": "hormuz_blockade"})
    assert resp.status_code == 404

    get_settings.cache_clear()


# ════════════════════════════════════════════════════════════════════════
# 2. hormuz_blockade preset
# ════════════════════════════════════════════════════════════════════════
def test_inject_hormuz_creates_mission(monkeypatch):
    client = _make_client_with_demo(True, monkeypatch)

    resp = client.post("/api/demo/inject_signal", json={"scenario": "hormuz_blockade"})
    assert resp.status_code == 200, resp.text

    data = resp.json()
    assert data["source"] == "demo_inject"
    m = data["mission"]
    assert m["mission_type"] == "HEDGE"
    assert m["urgency"] == "urgent"
    assert m["pattern_score"] == 82.0
    assert m["goal_text"] == "Term 60% → 75% (4주)"
    assert m["target_pct"] == 75
    assert m["duration_days"] == 28
    assert m["source"] == "demo_inject"

    get_settings.cache_clear()


def test_inject_ceasefire_creates_opportunity(monkeypatch):
    client = _make_client_with_demo(True, monkeypatch)

    resp = client.post("/api/demo/inject_signal", json={"scenario": "ceasefire"})
    assert resp.status_code == 200

    m = resp.json()["mission"]
    assert m["mission_type"] == "OPPORTUNITY"
    assert m["pattern_score"] == 78.0
    assert "휴전" in m["reasoning"]

    get_settings.cache_clear()


# ════════════════════════════════════════════════════════════════════════
# 3. Custom scenario validation
# ════════════════════════════════════════════════════════════════════════
def test_inject_custom_requires_fields(monkeypatch):
    client = _make_client_with_demo(True, monkeypatch)

    # custom 인데 mission_type / goal_text / reasoning 누락
    resp = client.post("/api/demo/inject_signal", json={"scenario": "custom"})
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["code"] == "CUSTOM_REQUIRES_FIELDS"

    get_settings.cache_clear()


def test_inject_custom_with_fields_succeeds(monkeypatch):
    client = _make_client_with_demo(True, monkeypatch)

    resp = client.post(
        "/api/demo/inject_signal",
        json={
            "scenario": "custom",
            "mission_type": "HEDGE",
            "goal_text": "Custom test goal",
            "reasoning": "Custom test reasoning",
            "pattern_score": 50.0,
        },
    )
    assert resp.status_code == 200, resp.text
    m = resp.json()["mission"]
    assert m["goal_text"] == "Custom test goal"
    assert m["pattern_score"] == 50.0

    get_settings.cache_clear()


# ════════════════════════════════════════════════════════════════════════
# 4. Invalid scenario
# ════════════════════════════════════════════════════════════════════════
def test_invalid_scenario_returns_422(monkeypatch):
    client = _make_client_with_demo(True, monkeypatch)

    resp = client.post("/api/demo/inject_signal", json={"scenario": "nonexistent"})
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["code"] == "INVALID_SCENARIO"
    assert "hormuz_blockade" in detail["valid"]

    get_settings.cache_clear()


# ════════════════════════════════════════════════════════════════════════
# 5. EventBus 'mission.proposed' 발행 검증
# ════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_inject_publishes_bus_event(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    get_settings.cache_clear()

    from app.store import reset_store_for_testing, get_bus
    from app.main import create_app
    reset_store_for_testing()
    app = create_app()
    bus = get_bus()
    sub_q = await bus.subscribe()

    # TestClient는 sync — 직접 endpoint 호출 대신 httpx AsyncClient 또는 sync wrap
    from fastapi.testclient import TestClient
    client = TestClient(app)
    resp = client.post("/api/demo/inject_signal", json={"scenario": "hormuz_blockade"})
    assert resp.status_code == 200

    event = await asyncio.wait_for(sub_q.get(), timeout=2.0)
    assert event["type"] == "mission.proposed"
    assert event["mission"]["source"] == "demo_inject"
    assert event["mission"]["mission_type"] == "HEDGE"

    await bus.unsubscribe(sub_q)
    get_settings.cache_clear()


# ════════════════════════════════════════════════════════════════════════
# 6. 연속 inject → 별도 mission_id
# ════════════════════════════════════════════════════════════════════════
def test_inject_twice_creates_two_missions(monkeypatch):
    client = _make_client_with_demo(True, monkeypatch)

    r1 = client.post("/api/demo/inject_signal", json={"scenario": "hormuz_blockade"})
    r2 = client.post("/api/demo/inject_signal", json={"scenario": "hormuz_blockade"})
    assert r1.status_code == 200 and r2.status_code == 200

    mid1 = r1.json()["mission"]["mission_id"]
    mid2 = r2.json()["mission"]["mission_id"]
    assert mid1 != mid2

    # /api/missions/active 에 둘 다 포함 (다른 mission 도 있을 수 있어 subset check)
    active = client.get("/api/missions/active").json()["missions"]
    ids = {m["mission_id"] for m in active}
    assert mid1 in ids
    assert mid2 in ids

    get_settings.cache_clear()


# ════════════════════════════════════════════════════════════════════════
# 7. slack_status reflects settings.slack_enabled
# ════════════════════════════════════════════════════════════════════════
def test_slack_status_dryrun_when_token_missing(monkeypatch):
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    monkeypatch.delenv("SLACK_SIGNING_SECRET", raising=False)
    monkeypatch.delenv("SLACK_DEFAULT_CHANNEL", raising=False)
    client = _make_client_with_demo(True, monkeypatch)

    resp = client.post("/api/demo/inject_signal", json={"scenario": "saudi_cut"})
    assert resp.status_code == 200
    assert resp.json()["slack_status"] == "dry-run"

    get_settings.cache_clear()
