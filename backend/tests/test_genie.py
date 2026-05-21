"""Genie endpoint fallback path tests.

Live SDK 호출 test는 workspace 의존이라 skip (LAKEBASE_HOST gated pattern과 동일).
본 test는 GENIE_SPACE_ID 미설정 또는 SDK 실패 시 fallback 분기 검증.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings


def _client(monkeypatch, genie_enabled: bool = False) -> TestClient:
    if genie_enabled:
        monkeypatch.setenv("GENIE_SPACE_ID", "fake_space_id_for_test")
    else:
        monkeypatch.delenv("GENIE_SPACE_ID", raising=False)
    get_settings.cache_clear()

    from app.main import create_app
    return TestClient(create_app())


# ════════════════════════════════════════════════════════════════════════
# 1. GENIE_SPACE_ID 미설정 → fallback
# ════════════════════════════════════════════════════════════════════════
def test_genie_disabled_returns_fallback(monkeypatch):
    client = _client(monkeypatch, genie_enabled=False)
    resp = client.post(
        "/api/genie/query",
        json={"question": "최근 OPEC 사우디 감산 시그널 어때?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] in ("fallback_data", "fallback_text")
    assert len(body["answer"]) > 0
    get_settings.cache_clear()


# ════════════════════════════════════════════════════════════════════════
# 2. Question validation
# ════════════════════════════════════════════════════════════════════════
def test_genie_question_validation(monkeypatch):
    client = _client(monkeypatch, genie_enabled=False)
    resp = client.post("/api/genie/query", json={"question": ""})
    assert resp.status_code == 422

    resp2 = client.post("/api/genie/query", json={"question": "a" * 501})
    assert resp2.status_code == 422
    get_settings.cache_clear()


# ════════════════════════════════════════════════════════════════════════
# 3. Keyword matching — 'OPEC' → MOMR preset
# ════════════════════════════════════════════════════════════════════════
def test_genie_keyword_opec(monkeypatch):
    client = _client(monkeypatch, genie_enabled=False)
    resp = client.post(
        "/api/genie/query",
        json={"question": "OPEC 사우디 공급 변화 알려줘"},
    )
    assert resp.status_code == 200
    body = resp.json()
    # 'fallback_data' (Lakebase 성공) 또는 'fallback_text' (Lakebase 실패) — 어느 쪽이든
    # source에 'fallback_' prefix + 답변에 OPEC/MOMR/사우디 키워드 포함
    assert body["source"].startswith("fallback")
    answer = body["answer"]
    assert any(kw in answer for kw in ["OPEC", "MOMR", "사우디"])
    get_settings.cache_clear()


def test_genie_keyword_dubai(monkeypatch):
    client = _client(monkeypatch, genie_enabled=False)
    resp = client.post(
        "/api/genie/query",
        json={"question": "두바이유 momentum 어때?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"].startswith("fallback")
    assert any(kw in body["answer"] for kw in ["Dubai", "두바이", "종가"])
    get_settings.cache_clear()


# ════════════════════════════════════════════════════════════════════════
# 4. Unknown question → generic fallback
# ════════════════════════════════════════════════════════════════════════
def test_genie_unknown_returns_generic(monkeypatch):
    client = _client(monkeypatch, genie_enabled=False)
    resp = client.post(
        "/api/genie/query",
        json={"question": "오늘 점심 뭐 먹을까?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "fallback"
    assert "Genie Space" in body["answer"]
    get_settings.cache_clear()


# ════════════════════════════════════════════════════════════════════════
# 5. genie_enabled=True + SDK raise → graceful fallback
# ════════════════════════════════════════════════════════════════════════
def test_genie_live_failure_falls_back(monkeypatch):
    client = _client(monkeypatch, genie_enabled=True)

    # query_genie를 force raise
    async def _force_fail(question, conv_id):
        raise RuntimeError("simulated SDK failure")

    with patch("app.api.genie.query_genie", _force_fail):
        resp = client.post(
            "/api/genie/query",
            json={"question": "두바이유 momentum 어때?"},
        )

    assert resp.status_code == 200
    body = resp.json()
    # live 실패 후 fallback 진입
    assert body["source"].startswith("fallback")
    get_settings.cache_clear()


# ════════════════════════════════════════════════════════════════════════
# 6. Health endpoint
# ════════════════════════════════════════════════════════════════════════
def test_genie_health_disabled(monkeypatch):
    client = _client(monkeypatch, genie_enabled=False)
    resp = client.get("/api/genie/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["enabled"] is False
    assert "(missing)" in body["space_id"]
    assert body["fallback_available"] is True
    get_settings.cache_clear()


def test_genie_health_enabled(monkeypatch):
    client = _client(monkeypatch, genie_enabled=True)
    resp = client.get("/api/genie/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["enabled"] is True
    assert body["space_id"] == "fake_space_id_for_test"
    get_settings.cache_clear()
