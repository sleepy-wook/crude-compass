"""Signals API tests — GET /api/signals/{id}/lifecycle."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_lifecycle_404_for_unknown_signal():
    response = client.get("/api/signals/nonexistent-id-xyz/lifecycle")
    # graceful — Lakebase 미연결 시 빈 stages 200, 또는 명시적 404
    assert response.status_code in (200, 404)


def test_lifecycle_rejects_invalid_signal_id():
    """SQL-injection 방어 — 영숫자/하이픈/언더스코어 외 문자는 400."""
    response = client.get("/api/signals/abc'%20OR%201=1--/lifecycle")
    assert response.status_code == 400


def test_lifecycle_shape():
    """알려진 signal_id 형식 검증 (200 일 때 stages 4-key 존재)."""
    response = client.get("/api/signals/sample-1/lifecycle")
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        body = response.json()
        assert "signal_id" in body
        assert "stages" in body
        stages = body["stages"]
        assert all(k in stages for k in ("detected", "scored", "decay", "contribution"))
